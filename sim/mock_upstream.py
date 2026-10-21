"""Minimal OpenAI-compatible inference backend used by the SUAY simulation.

It exists so the token-policy layer can be exercised without a GPU, Petals or network access.
Both modes are supported: a JSON completion and an SSE stream.
"""
import json
import os
import time

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)


@app.get('/healthz')
def health():
    return {'ok': True}


@app.post('/v1/chat/completions')
async def completions(request: Request):
    payload = await request.json()
    prompt = ' '.join(m.get('content', '') for m in payload.get('messages', []))
    answer = 'simulated answer to: ' + prompt[:120]
    model = payload.get('model', 'unknown')
    # Deterministic fake accounting: 4 prompt tokens + 3 completion tokens.
    usage = {'prompt_tokens': 4, 'completion_tokens': 3, 'total_tokens': 7}

    if not payload.get('stream'):
        return JSONResponse({
            'id': 'chatcmpl-sim',
            'object': 'chat.completion',
            'created': int(time.time()),
            'model': model,
            'choices': [{'index': 0, 'message': {'role': 'assistant', 'content': answer}, 'finish_reason': 'stop'}],
            'usage': usage,
        })

    async def events():
        for word in answer.split(' '):
            chunk = {'choices': [{'index': 0, 'delta': {'content': word + ' '}}]}
            yield ('data: ' + json.dumps(chunk) + '\n\n').encode()
        # A real backend reports usage in the final chunk; the policy layer must read it.
        final = {'choices': [], 'usage': {'prompt_tokens': 4, 'completion_tokens': 3, 'total_tokens': 3}}
        yield ('data: ' + json.dumps(final) + '\n\n').encode()
        yield b'data: [DONE]\n\n'

    return StreamingResponse(events(), media_type='text/event-stream')


if __name__ == '__main__':
    uvicorn.run(app, host='127.0.0.1', port=int(os.getenv('SIM_UPSTREAM_PORT', '9077')), log_level='warning')
