use serde::{Deserialize, Serialize};
use std::{collections::VecDeque, env, fs, path::PathBuf, process::{Child, Command}, sync::{Arc, atomic::{AtomicBool, Ordering}}, thread, time::{Duration, Instant}};
use sysinfo::{Pid, System};

const MIB: u64 = 1024 * 1024;

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Config {
    executable: PathBuf,
    #[serde(default)]
    args: Vec<String>,
    max_backend_memory_mib: u64,
    host_reserve_mib: u64,
    resume_headroom_mib: u64,
    #[serde(default = "poll_default")]
    poll_seconds: u64,
}
fn poll_default() -> u64 { 2 }
impl Config {
    fn validate(&self) -> Result<(), String> {
        if !self.executable.is_absolute() || !self.executable.is_file() { return Err("Executable must be an existing absolute local path".into()); }
        if self.max_backend_memory_mib == 0 || self.host_reserve_mib == 0 || self.resume_headroom_mib <= self.host_reserve_mib { return Err("Positive memory budgets and resume headroom greater than reserve are required".into()); }
        if !(1..=60).contains(&self.poll_seconds) || self.args.len() > 100 { return Err("Invalid polling interval or argument count".into()); }
        for amount in [self.max_backend_memory_mib, self.host_reserve_mib, self.resume_headroom_mib] {
            if amount.checked_mul(MIB).is_none() { return Err("Memory budget overflow".into()); }
        }
        Ok(())
    }
}

#[derive(Serialize)]
struct Snapshot { total_memory_bytes: u64, available_memory_bytes: u64, cpu_threads: usize, system_cpu_percent: f32, backend_memory_bytes: u64 }
fn snapshot(system: &mut System, pid: Option<u32>) -> Snapshot {
    system.refresh_all();
    let mut total = system.total_memory();
    let mut available = system.available_memory();
    #[cfg(target_os = "linux")]
    if let (Ok(max), Ok(current)) = (fs::read_to_string("/sys/fs/cgroup/memory.max"), fs::read_to_string("/sys/fs/cgroup/memory.current")) {
        if let (Ok(max), Ok(current)) = (max.trim().parse::<u64>(), current.trim().parse::<u64>()) {
            total = total.min(max); available = available.min(max.saturating_sub(current));
        }
    }
    #[cfg(not(target_os = "linux"))]
    let _ = (&mut total, &mut available);
    let mut ids = pid.map(|id| vec![Pid::from_u32(id)]).unwrap_or_default();
    loop {
        let mut found = false;
        for (id, p) in system.processes() {
            if !ids.contains(id) && p.parent().is_some_and(|parent| ids.contains(&parent)) { ids.push(*id); found = true; }
        }
        if !found { break; }
    }
    let memory = ids.iter().filter_map(|id| system.process(*id)).fold(0u64, |sum,p| sum.saturating_add(p.memory()));
    Snapshot { total_memory_bytes: total, available_memory_bytes: available, cpu_threads: system.cpus().len(), system_cpu_percent: system.global_cpu_usage(), backend_memory_bytes: memory }
}

fn can_start(available: u64, budget: u64, headroom: u64) -> bool {
    budget.checked_add(headroom).is_some_and(|required| available >= required)
}
fn should_stop(available: u64, used: u64, budget: u64, reserve: u64) -> bool { available < reserve || used > budget }
fn retry_delay(failures: u32) -> Duration { Duration::from_secs(5u64.saturating_mul(1u64 << failures.min(6)).min(300)) }

#[cfg(windows)]
struct Job(windows_sys::Win32::Foundation::HANDLE);
#[cfg(windows)]
impl Drop for Job { fn drop(&mut self) { unsafe { windows_sys::Win32::Foundation::CloseHandle(self.0); } } }
#[cfg(windows)]
fn attach_job(child: &Child, budget: u64) -> Result<Job, String> {
    use std::os::windows::io::AsRawHandle;
    use windows_sys::Win32::System::JobObjects::*;
    unsafe {
        let handle = CreateJobObjectW(std::ptr::null(), std::ptr::null());
        if handle.is_null() { return Err(std::io::Error::last_os_error().to_string()); }
        let job = Job(handle);
        let mut limits: JOBOBJECT_EXTENDED_LIMIT_INFORMATION = std::mem::zeroed();
        limits.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE | JOB_OBJECT_LIMIT_JOB_MEMORY;
        limits.JobMemoryLimit = usize::try_from(budget).map_err(|_| "Budget does not fit platform")?;
        if SetInformationJobObject(handle, JobObjectExtendedLimitInformation, &limits as *const _ as *const _, std::mem::size_of_val(&limits) as u32) == 0 || AssignProcessToJobObject(handle, child.as_raw_handle()) == 0 {
            return Err(std::io::Error::last_os_error().to_string());
        }
        Ok(job)
    }
}

struct Backend {
    child: Child,
    #[cfg(windows)] job: Option<Job>,
}
impl Backend {
    fn spawn(config: &Config) -> Result<Self, String> {
        let mut cmd = Command::new(&config.executable); cmd.args(&config.args);
        #[cfg(unix)] { use std::os::unix::process::CommandExt; cmd.process_group(0); }
        #[cfg(windows)] { use std::os::windows::process::CommandExt; cmd.creation_flags(0x08000000); }
        let mut child = cmd.spawn().map_err(|e| e.to_string())?;
        #[cfg(windows)] {
            match attach_job(&child, config.max_backend_memory_mib * MIB) {
                Ok(job) => Ok(Self { child, job: Some(job) }),
                Err(e) => { let _ = child.kill(); let _ = child.wait(); Err(format!("Failed to enforce Windows Job limits: {e}")) }
            }
        }
        #[cfg(not(windows))] { let _ = &mut child; Ok(Self { child }) }
    }
    fn stop(&mut self) {
        #[cfg(windows)] { self.job.take(); }
        #[cfg(unix)] unsafe { libc::kill(-(self.child.id() as i32), libc::SIGTERM); }
        let deadline = Instant::now() + Duration::from_secs(2);
        while Instant::now() < deadline {
            if matches!(self.child.try_wait(), Ok(Some(_))) { break; }
            thread::sleep(Duration::from_millis(50));
        }
        #[cfg(unix)] unsafe { libc::kill(-(self.child.id() as i32), libc::SIGKILL); }
        let _ = self.child.kill(); let _ = self.child.wait();
    }
}
impl Drop for Backend { fn drop(&mut self) { self.stop(); } }

fn run(config: Config) -> Result<(), String> {
    config.validate()?;
    let running = Arc::new(AtomicBool::new(true)); let signal = running.clone();
    ctrlc::set_handler(move || signal.store(false, Ordering::SeqCst)).map_err(|e| e.to_string())?;
    let mut system = System::new_all();
    let mut backend: Option<Backend> = None;
    let mut starts = VecDeque::new();
    let mut retry = Instant::now(); let mut failures = 0;
    while running.load(Ordering::SeqCst) {
        let now = Instant::now();
        while starts.front().is_some_and(|t: &Instant| now.duration_since(*t) >= Duration::from_secs(600)) { starts.pop_front(); }
        let state = snapshot(&mut system, backend.as_ref().map(|b| b.child.id()));
        let mut reason = "monitoring";
        if let Some(child) = backend.as_mut() {
            let exited = child.child.try_wait().map_err(|e| e.to_string())?.is_some();
            if exited || should_stop(state.available_memory_bytes, state.backend_memory_bytes, config.max_backend_memory_mib*MIB, config.host_reserve_mib*MIB) {
                backend.take(); failures += 1; retry = now + retry_delay(failures);
                reason = if exited { "backend_exited" } else { "memory_protection_stop" };
            }
        } else if now >= retry && starts.len() < 5 && can_start(state.available_memory_bytes, config.max_backend_memory_mib*MIB, config.resume_headroom_mib*MIB) {
            starts.push_back(now);
            match Backend::spawn(&config) {
                Ok(child) => { backend = Some(child); reason = "backend_started"; },
                Err(error) => { eprintln!("{error}"); failures += 1; retry = now + retry_delay(failures); reason = "start_failed"; }
            }
        } else { reason = "waiting_for_memory_or_restart_budget"; }
        println!("{}", serde_json::json!({"event":reason,"backend_running":backend.is_some(),"resources":state}));
        for _ in 0..config.poll_seconds*10 { if !running.load(Ordering::SeqCst) { break; } thread::sleep(Duration::from_millis(100)); }
    }
    drop(backend); Ok(())
}

fn main() {
    let args: Vec<String> = env::args().collect();
    let result = match args.get(1).map(String::as_str) {
        Some("status") => { let mut system = System::new_all(); thread::sleep(Duration::from_millis(250)); println!("{}", serde_json::to_string_pretty(&snapshot(&mut system, None)).unwrap()); Ok(()) },
        Some("check") | Some("run") if args.len() == 3 => fs::read_to_string(&args[2]).map_err(|e| e.to_string())
            .and_then(|text| serde_json::from_str::<Config>(&text).map_err(|e| e.to_string()))
            .and_then(|config| if args[1] == "check" { config.validate().map(|_| println!("Local config is valid")) } else { run(config) }),
        _ => Err("Usage: suay-resource-agent status | check <local.json> | run <local.json>".into()),
    };
    if let Err(error) = result { eprintln!("{error}"); std::process::exit(1); }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test] fn admission_reserves_memory_and_rejects_overflow() { assert!(can_start(12,8,4));assert!(!can_start(11,8,4));assert!(!can_start(u64::MAX,u64::MAX,1)); }
    #[test] fn hysteresis_protects_host_and_backend_budget() { assert!(should_stop(3,8,8,4));assert!(should_stop(10,9,8,4));assert!(!should_stop(4,8,8,4)); }
    #[test] fn restart_delay_is_bounded() { assert_eq!(retry_delay(0).as_secs(),5);assert_eq!(retry_delay(100).as_secs(),300); }
    #[test] fn config_rejects_unknown_remote_command_fields() { assert!(serde_json::from_str::<Config>(r#"{"executable":"/bin/true","args":[],"max_backend_memory_mib":1,"host_reserve_mib":1,"resume_headroom_mib":2,"shell":"whoami"}"#).is_err()); }
    #[test] fn zero_budget_cannot_start() { let c=Config{executable:env::current_exe().unwrap(),args:vec![],max_backend_memory_mib:0,host_reserve_mib:1,resume_headroom_mib:2,poll_seconds:2};assert!(c.validate().is_err()); }
}
