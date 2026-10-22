from pathlib import Path

p = Path('pasadhi/app/group.py')
t = p.read_text(encoding='utf-8')

old_start = t.index('def node_hours_available(')
old_end = t.index('def economics(')
new_block = '''def machine_hours_month(group: Group, days=30) -> list:
    """Usable hours per machine type per month, honouring each machine's own utilisation."""
    weekday_days, weekend_days = 22, 8
    rows = []
    for machine in group.machines:
        hours = 0.0
        for band, (start, end) in BANDS.items():
            span = end - start
            usable = max(0.0, min(group.share_pct, 1.0 - machine.profile[band]))
            weekday = span if band != 'night' else 24  # night band is charged daily below
            if band == 'night':
                hours += usable * span * days
            else:
                hours += usable * span * weekday_days + usable * span * weekend_days
        rows.append({'machine': machine, 'hours_month': hours * machine.nodes})
    return rows


def node_hours_available(group: Group, days=30) -> dict:
    rows = machine_hours_month(group, days)
    total = sum(row['hours_month'] for row in rows)
    threads = sum(m.threads * m.nodes for m in group.machines)
    machines = sum(m.nodes for m in group.machines)
    return {'node_hours_month': round(total, 0),
            'thread_hours_month': round(total * (threads / max(1, machines)), 0)}


'''
t = t[:old_start] + new_block + t[old_end:]

old_econ_start = t.index('def economics(')
old_econ_end = t.index('def default_office(')
new_econ = '''def economics(group: Group) -> dict:
    from pasadhi.app import impact

    totals = group.totals()
    rows = machine_hours_month(group)
    shared = 0.0
    for row in rows:
        machine = row['machine']
        result = impact.node_value(
            impact.Share(cpu_pct=int(group.share_pct * 100), gpu_pct=0, ram_pct=int(group.share_pct * 100),
                         disk_pct=int(group.share_pct * 100), network_pct=int(group.share_pct * 100)),
            threads=machine.threads, ram_gb=32.0, vram_gb=0.0)
        shared += row['hours_month'] * result['hourly_thb']

    list_price = (LIST_PRICE_THB * (1 - GROUP_DISCOUNT) if group.plan != 'premium'
                  else PREMIUM_PRICE_THB * (1 - GROUP_DISCOUNT * 0.5))
    subscription = list_price * totals['machines']

    if group.mode == 'internal':
        net = -subscription
    elif group.mode == 'shared':
        net = shared
    else:
        reserved = group.reserve_pct / max(group.share_pct, 1e-9)
        net = shared * (1 - reserved) - subscription

    return {
        'machines': totals['machines'],
        'threads': totals['threads'],
        'peak_gflops': totals['peak_gflops'],
        'shared_capacity_gflops': round(totals['peak_gflops'] * group.share_pct, 1),
        'node_hours_month': node_hours_available(group)['node_hours_month'],
        'shared_earnings_thb_month': round(shared, 0),
        'subscription_thb_month': round(subscription, 0),
        'net_thb_month': round(net, 0),
        'per_node_month': round(net / totals['machines'], 0),
    }


'''
t = t[:old_econ_start] + new_econ + t[old_econ_end:]

if 'from pasadhi.app import impact' not in t.split('def economics')[0]:
    pass
p.write_text(t, encoding='utf-8')
print('group.py patched')
