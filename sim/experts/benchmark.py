"""Domain-expert routing benchmark + capacity model.

Measured: a rule-based router classifies queries and their referenced sources into legal / chemistry /
general. The labelled set has three difficulty tiers, including the ambiguous cases that a substring matcher
gets wrong on purpose (e.g. "สัญญาณ NMR" contains "สัญญา").

Modelled: per-request latency, fleet capacity and node footprint for three deployment shapes, using the
gateway floor measured in `report/REPORT.md` and documented compute rates.

    python sim/experts/benchmark.py --out report/experts
"""
import argparse
import json
import random
import statistics
import time
from pathlib import Path

random.seed(11)
DOMAINS = ['legal', 'chemistry', 'general']

LEGAL_TERMS = ['สัญญา', 'มาตรา', 'กฎหมาย', 'คดี', 'ศาล', 'ทนาย', 'ฟ้อง', 'ละเมิด', 'คำพิพากษา', 'สิทธิ',
               'ลิขสิทธิ์', 'เครื่องหมายการค้า', 'ข้อบังคับ', 'พ.ร.บ.', 'ความรับผิด', 'ค่าเสียหาย',
               'contract', 'clause', 'statute', 'litigation', 'liability', 'nda', 'tort', 'damages',
               'plaintiff', 'arbitration', 'indemnity']
CHEM_TERMS = ['โมล', 'กรด', 'เบส', 'ไทเทรต', 'สารละลาย', 'ความเข้มข้น', 'ปฏิกิริยา', 'ตัวทำละลาย', 'พอลิเมอร์',
              'ผลึก', 'มวลโมเลกุล', 'ออกซิเดชัน', 'ตัวเร่ง', 'การกลั่น',
              'molarity', 'titration', 'solvent', 'polymer', 'crystal', 'catalyst', 'oxidation',
              'distillation', 'spectroscopy', 'nmr', 'hplc', 'reagent', 'ph', 'synthesis', 'stoichiometry']
SOURCE_HINTS = {
    'legal': ['สัญญา', 'contract', 'พ.ร.บ', 'act', 'คำพิพากษา', 'judgment', 'complaint'],
    'chemistry': ['msds', 'sds', 'lab', 'spectrum', 'assay', 'coa', 'chromatogram'],
}


def score(text, terms):
    lowered = text.lower()
    return sum(1.0 for term in terms if term.lower() in lowered)


def route(query, source=''):
    text = f'{query} {source}'
    scores = {'legal': score(text, LEGAL_TERMS), 'chemistry': score(text, CHEM_TERMS)}
    for domain, hints in SOURCE_HINTS.items():
        if any(hint.lower() in source.lower() for hint in hints):
            scores[domain] += 3.0
    best = max(scores, key=scores.get)
    top = scores[best]
    second = max(value for key, value in scores.items() if key != best)
    if top < 1.0:
        return 'general', 0.0, scores
    confidence = (top - second) / (top + second) if top + second else 0.0
    return best, round(confidence, 3), scores


def build_dataset(per_tier=1200):
    """Three tiers: easy (clear terms), ambiguous (two domains), adversarial (substring traps, source-only)."""
    easy = {
        'legal': [('สัญญาจ้างมีข้อจำกัดความรับผิดอย่างไร', 'สัญญาจ้าง.pdf'),
                  ('มาตรา 420 เรื่องละเมิดใช้อย่างไร', ''),
                  ('draft a litigation hold notice', 'complaint.docx')],
        'chemistry': [('คำนวณโมลของ NaOH 0.5 M', ''),
                      ('ไทเทรตกรดอะซิติกด้วยเบสแก่', 'lab_report.pdf'),
                      ('interpret this NMR spectrum', 'spectrum_run7.csv')],
        'general': [('สรุปนโยบายลาพักร้อน', 'policy.pdf'),
                    ('ช่วยเขียนอีเมลขอบคุณลูกค้า', ''),
                    ('how do I reset my ticket password in the portal', '')],
    }
    ambiguous = [
        ('สัญญาซื้อขายสารเคมีในห้องแล็บ ต้องระบุความเข้มข้นไหม', 'สัญญาซื้อขาย.pdf', 'legal'),
        ('ซื้อกรดซัลฟิวริกผิดสเปก ฟ้องเรียกค่าเสียหายได้หรือไม่', 'invoice.pdf', 'legal'),
        ('สัญญาจ้างนักเคมีวิเคราะห์ ต้องมีข้อกำหนดความปลอดภัยอะไร', 'สัญญาจ้าง.pdf', 'legal'),
        ('สารที่ระบุในสัญญาซื้อขายมีความบริสุทธิ์ตามข้อตกลงหรือไม่', 'coa.pdf', 'chemistry'),
    ]
    adversarial = [
        ('สัญญาณ NMR ของตัวอย่างนี้แปลผลอย่างไร', '', 'chemistry'),      # "สัญญา" inside "สัญญาณ"
        ('วิเคราะห์สเปกตรัม IR เทียบกับฐานข้อมูล', '', 'chemistry'),
        ('มาตรฐานความปลอดภัยของห้องปฏิบัติการเคมี', '', 'chemistry'),
        ('rights and obligations under the supply agreement', '', 'legal'),
        ('ph level of the solvent after dilution', '', 'chemistry'),
        ('ค่า pH ของสารละลายหลังเจือจาง', '', 'chemistry'),
        ('สรุปค่าใช้จ่ายในใบเสร็จ', '', 'general'),
        ('วิธีขอใบรับรองผลการวิเคราะห์ (COA)', 'request_form.pdf', 'general'),
    ]
    rows = []
    for _ in range(per_tier):
        for domain, items in easy.items():
            query, source = random.choice(items)
            rows.append({'tier': 'easy', 'query': query, 'source': source, 'label': domain})
        query, source, label = random.choice(ambiguous)
        rows.append({'tier': 'ambiguous', 'query': query, 'source': source, 'label': label})
        query, source, label = random.choice(adversarial)
        rows.append({'tier': 'adversarial', 'query': query, 'source': source, 'label': label})
    random.shuffle(rows)
    return rows


def evaluate(rows):
    confusion = {label: {pred: 0 for pred in DOMAINS} for label in DOMAINS}
    per_tier = {}
    latencies = []
    correct = 0
    for row in rows:
        started = time.perf_counter()
        predicted, _, _ = route(row['query'], row['source'])
        latencies.append((time.perf_counter() - started) * 1e6)
        confusion[row['label']][predicted] += 1
        hit = predicted == row['label']
        correct += hit
        tier = per_tier.setdefault(row['tier'], {'total': 0, 'correct': 0})
        tier['total'] += 1
        tier['correct'] += hit

    per_class = {}
    for domain in DOMAINS:
        tp = confusion[domain][domain]
        fp = sum(confusion[other][domain] for other in DOMAINS if other != domain)
        fn = sum(confusion[domain][other] for other in DOMAINS if other != domain)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_class[domain] = {'precision': round(precision, 4), 'recall': round(recall, 4), 'f1': round(f1, 4)}

    ordered = sorted(latencies)
    scored = []
    for row in rows:
        predicted, confidence, _ = route(row['query'], row['source'])
        scored.append((row['label'], predicted, confidence))
    sweep = []
    for threshold in [0.0, 0.1, 0.2, 0.3, 0.4, 0.5]:
        kept = [item for item in scored if item[2] >= threshold]
        if not kept:
            continue
        sweep.append({'threshold': threshold,
                      'coverage': round(len(kept) / len(scored), 4),
                      'accuracy': round(sum(1 for label, pred, _ in kept if label == pred) / len(kept), 4)})
    return {
        'samples': len(rows),
        'accuracy': round(correct / len(rows), 4),
        'accuracy_by_tier': {tier: round(values['correct'] / values['total'], 4)
                             for tier, values in per_tier.items()},
        'per_class': per_class,
        'confusion': confusion,
        'confidence_sweep': sweep,
        'latency_us': {
            'mean': round(statistics.fmean(ordered), 1),
            'p50': round(ordered[int(0.50 * (len(ordered) - 1))], 1),
            'p95': round(ordered[int(0.95 * (len(ordered) - 1))], 1),
            'p99': round(ordered[int(0.99 * (len(ordered) - 1))], 1),
            'max': round(ordered[-1], 1),
        },
    }


def model(measured_gateway_s=0.098, answer_steps=150.0, fleet=50, usable_gb=1.1):
    """Capacity model. Parallel copies, not single-request latency, decide fleet throughput."""
    shapes = {
        'dense_8b': {'label': 'Dense 8B (one catalogue for all queries)', 'active_b': 8.0,
                     'copy_gb': 16.0, 'steps_per_s': 3.0, 'pools': 1},
        'moe_8x7b': {'label': 'MoE 8×7B, top-2 (one shared catalogue)', 'active_b': 13.0,
                     'copy_gb': 94.0, 'steps_per_s': 1.85, 'pools': 1},
        'domain_experts': {'label': '8 domain experts 1B + shared 1B, routed', 'active_b': 2.0,
                           'copy_gb': 4.0, 'steps_per_s': 12.0, 'pools': 8},
    }
    rows = []
    for key, shape in shapes.items():
        nodes_per_copy = int(-(-shape['copy_gb'] // usable_gb))
        nodes_total = nodes_per_copy * shape['pools']
        copies = (fleet // nodes_per_copy) if shape['pools'] == 1 else min(shape['pools'], fleet // nodes_per_copy)
        latency = measured_gateway_s + answer_steps / shape['steps_per_s']
        capacity = copies / latency if latency else 0.0
        rows.append({
            'shape': key,
            'label': shape['label'],
            'active_b': shape['active_b'],
            'copy_gb': shape['copy_gb'],
            'nodes_per_copy': nodes_per_copy,
            'nodes_total': nodes_total,
            'fits_50': nodes_total <= fleet,
            'parallel_copies': copies,
            'latency_s': round(latency, 2),
            'fleet_rps': round(capacity, 3),
            'node_hours_per_10k': round(10000 * latency * nodes_total / 3600, 1),
        })
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', default='report/experts')
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    rows = build_dataset()
    result = evaluate(rows)
    shapes = model()
    (out / 'router_metrics.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    (out / 'shapes.json').write_text(json.dumps({'gateway_s': 0.098, 'answer_steps': 150,
                                                 'fleet': 50, 'shapes': shapes}, indent=2), encoding='utf-8')
    (out / 'dataset_sample.json').write_text(json.dumps(rows[:24], ensure_ascii=False, indent=2), encoding='utf-8')

    print(f"samples {result['samples']} accuracy {result['accuracy']:.4f} by tier {result['accuracy_by_tier']}")
    for domain, scores in result['per_class'].items():
        print(f"  {domain:10s} P {scores['precision']:.3f} R {scores['recall']:.3f} F1 {scores['f1']:.3f}")
    print('  latency us p50 {p50} p95 {p95}'.format(**result['latency_us']))
    print('confusion', result['confusion'])
    for shape in shapes:
        print(f"  {shape['shape']:15s} latency {shape['latency_s']:7.2f}s  copies {shape['parallel_copies']:2d}  "
              f"fleet {shape['fleet_rps']:5.2f} rps  nodes {shape['nodes_total']:3d}  fits={shape['fits_50']}")


if __name__ == '__main__':
    main()
