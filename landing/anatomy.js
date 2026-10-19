/* Five illustrative steps. No telemetry or coordinator connection. */
(() => {
  const root = document.querySelector('[data-anatomy]');
  if (!root) return;
  const picture = root.querySelector('[data-anatomy-image]');
  const buttons = [...root.querySelectorAll('[data-anatomy-step]')];
  const toggle = root.querySelector('[data-anatomy-play]');
  const readout = root.querySelector('[data-anatomy-readout]');
  const base = root.dataset.assets;
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  let current = 0;
  let playing = false;
  let userPaused = false;
  let inView = false;
  let timer;

  function select(index) {
    current = (index + buttons.length) % buttons.length;
    buttons.forEach((button, i) => button.setAttribute('aria-pressed', String(i === current)));
    readout.textContent = buttons[current].dataset.description;
    if (!playing) picture.src = `${base}/step-${current + 1}.png`;
    picture.alt = `${current + 1}/5: ${buttons[current].textContent.trim()}. ${readout.textContent}`;
  }
  function pause() {
    playing = false;
    clearInterval(timer);
    toggle.textContent = toggle.dataset.play;
    toggle.setAttribute('aria-pressed', 'false');
    readout.setAttribute('aria-live', 'polite');
    select(current);
  }
  buttons.forEach((button, i) => button.addEventListener('click', () => {
    userPaused = true;
    pause();
    select(i);
  }));
  function play() {
    if (playing) return;
    playing = true;
    current = 0;
    readout.setAttribute('aria-live', 'off');
    select(0);
    picture.src = `${base}/suay-system-steps.gif`;
    toggle.textContent = toggle.dataset.pause;
    toggle.setAttribute('aria-pressed', 'true');
    timer = setInterval(() => select(current + 1), 3000);
  }
  function syncAutoplay() {
    if (document.hidden || !inView || reduced.matches) {
      if (playing) pause();
    } else if (!userPaused) {
      play();
    }
  }
  toggle.addEventListener('click', () => {
    userPaused = playing;
    if (playing) pause();
    else play();
  });
  document.addEventListener('visibilitychange', syncAutoplay);
  new IntersectionObserver(entries => {
    inView = entries[0].isIntersecting && entries[0].intersectionRatio >= 0.05;
    syncAutoplay();
  }, {threshold: 0.05}).observe(picture);
  reduced.addEventListener('change', syncAutoplay);
  select(0); // Autoplay when visible; respect reduced motion and explicit pauses.
})();
