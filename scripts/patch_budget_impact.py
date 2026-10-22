from pathlib import Path

p = Path('pasadhi/app/budget.py')
t = p.read_text(encoding='utf-8')
start = t.index('def hourly_earnings(')
end = t.index('def reference_check(')
new = '''def hourly_earnings(share: Share, cores: int, ram_gb: float, disk_free_gb: float, mbps: float,
                    vram_gb: float = 0.0) -> dict:
    """Payout follows the measured impact of each resource (`app/impact.py`), not a flat rate."""
    from pasadhi.app import impact

    result = impact.node_value(
        impact.Share(cpu_pct=share.cpu_pct, gpu_pct=share.gpu_pct, ram_pct=share.ram_pct,
                     disk_pct=share.disk_pct, network_pct=share.network_pct),
        threads=cores, ram_gb=ram_gb, vram_gb=vram_gb * (share.gpu_pct / 100))
    pool = result['detail']['cpu_pool_thb']
    contribution = result['contribution']
    return {
        'hourly_thb': result['hourly_thb'],
        'daily_thb': result['daily_thb'],
        'monthly_thb': result['monthly_thb'],
        'breakdown': {
            'cpu': round(contribution['CPU'] * pool, 3),
            'ram': round(contribution['RAM'] * pool, 3),
            'gpu': result['detail']['gpu_part'],
            'disk': round(contribution['DISK'] * pool, 3),
            'net': round(contribution['NET'] * pool, 3),
        },
        'weights': result['weights'],
        'weighted_fraction': result['weighted_fraction'],
    }


'''
p.write_text(t[:start] + new + t[end:], encoding='utf-8')
print('patched budget.py')
