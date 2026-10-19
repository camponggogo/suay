"""Interactive Petals client with LAN API discovery."""
import argparse
import json
import os
import socket
import urllib.request


def fetch_status(url):
    with urllib.request.urlopen(url.rstrip('/') + '/api/status', timeout=5) as response:
        status = json.load(response)
    if not status.get('initial_peers') or not status.get('current_model'):
        raise RuntimeError('Swarm bootstrap is not ready yet')
    return status


def discover(timeout=5):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(timeout)
        sock.sendto(b'{"type":"discover"}',
                    (os.getenv('BROADCAST_ADDRESS', '255.255.255.255'), int(os.getenv('DISCOVERY_PORT', '31338'))))
        import time
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            sock.settimeout(max(0.01, deadline - time.monotonic()))
            try:
                raw, addr = sock.recvfrom(8192)
                message = json.loads(raw)
                if message.get('type') == 'discovery':
                    return fetch_status(f"http://{addr[0]}:{int(message['api_port'])}")
            except (ValueError, KeyError, OSError, RuntimeError):
                continue
    raise RuntimeError('No ready LAN node found; use --coordinator http://IP:8080')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--coordinator', default=os.getenv('COORDINATOR_URL'))
    parser.add_argument('--max-new-tokens', type=int, default=128)
    args = parser.parse_args()
    if args.max_new_tokens <= 0:
        parser.error('--max-new-tokens must be positive')
    status = fetch_status(args.coordinator) if args.coordinator else discover()
    import torch
    from transformers import AutoTokenizer
    from petals import AutoDistributedModelForCausalLM
    name = status['current_model']
    print(f'Loading {name}. Model block coverage is checked when generating.')
    tokenizer = AutoTokenizer.from_pretrained(name)
    model = AutoDistributedModelForCausalLM.from_pretrained(name, initial_peers=status['initial_peers'])
    while True:
        try:
            prompt = input('\nYou (/quit to exit): ').strip()
        except (EOFError, KeyboardInterrupt):
            break
        if prompt == '/quit':
            break
        if not prompt:
            continue
        # Each prompt is independent so conversation history cannot exceed the context silently.
        if tokenizer.chat_template:
            prompt = tokenizer.apply_chat_template([{'role': 'user', 'content': prompt}],
                                                    tokenize=False, add_generation_prompt=True)
        inputs = tokenizer(prompt, return_tensors='pt')
        try:
            with torch.inference_mode():
                outputs = model.generate(**inputs, max_new_tokens=args.max_new_tokens,
                                         do_sample=True, temperature=0.7,
                                         pad_token_id=tokenizer.eos_token_id)
            print('AI:', tokenizer.decode(outputs[0, inputs['input_ids'].shape[1]:], skip_special_tokens=True))
        except Exception as exc:
            print(f'Generation failed: {exc}. Check node logs and model block coverage; retry the prompt.')


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, OSError, ValueError) as exc:
        raise SystemExit(str(exc))
