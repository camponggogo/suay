import json

d = json.load(open('report/growth/complexity_classes.json', encoding='utf-8'))
rows = d['table']
print('| class | nodes @n=500 | rps @n=500 | rps/100 nodes | dispatch | $/1M | ceiling reached at n |')
print('|---|---:|---:|---:|---:|---:|---:|')
for r in rows:
    x = r[-1]
    print('| {law} | {nodes:,} | {eff} | {eff100} | {disp:.0f} ms | {cost} | {hit} |'.format(
        law=x['law'], nodes=x['nodes'], eff=x['effective_rps'], eff100=x['rps_per_100_nodes'],
        disp=x['dispatch_ms'], cost=x['cost_per_mtok'], hit=d['ceiling_reached_at_n'][x['law']]))
print()
print('ceiling nodes:', d['constants']['nodes_for_ceiling'])
print('machine $/s:', round(d['constants']['machine_usd_s'], 9))
