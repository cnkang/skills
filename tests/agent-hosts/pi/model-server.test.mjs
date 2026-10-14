import assert from 'node:assert/strict';
import { test } from 'node:test';
import { createModelServer } from './model-server.mjs';

async function fixture(t, replies = []) {
  const model = createModelServer(replies);
  await new Promise(resolve => model.server.listen(0, '127.0.0.1', resolve));
  t.after(() => new Promise(resolve => {
    model.server.close(resolve);
    model.server.closeAllConnections();
  }));
  const url = `http://127.0.0.1:${model.server.address().port}/v1/chat/completions`;
  return { ...model, post: body => fetch(url, { method: 'POST', body }) };
}

test('Fixture malformed JSON returns no parser details', async (t) => {
  const { post, errors } = await fixture(t);
  const response = await post('private-parser-marker');
  assert.equal(response.status, 500);
  assert.equal(await response.text(), 'Fixture model request failed');
  assert.equal(errors.length, 1);
  assert.ok(errors[0] instanceof SyntaxError);
  assert.ok(errors[0].message.length > 0);
  assert.match(errors[0].stack, /model-server\.mjs/);
});

test('Fixture assertion failure returns no internal or request details', async (t) => {
  const { post, errors } = await fixture(t);
  const response = await post(JSON.stringify({ stream: true, model: 'private-model-marker' }));
  assert.equal(response.status, 500);
  assert.equal(await response.text(), 'Fixture model request failed');
  assert.equal(errors.length, 1);
  assert.ok(errors[0] instanceof assert.AssertionError);
  assert.match(errors[0].message, /private-model-marker/);
  assert.match(errors[0].stack, /model-server\.mjs/);
});

test('Fixture preserves text and read-tool streaming responses', async (t) => {
  const { post, requests, errors } = await fixture(t, ['Fixture complete', { path: 'SKILL.md' }]);
  for (const [index, finish] of ['stop', 'tool_calls'].entries()) {
    const request = { stream: true, model: 'ci-fixture', messages: [] };
    const response = await post(JSON.stringify(request));
    assert.equal(response.status, 200);
    assert.equal(response.headers.get('content-type'), 'text/event-stream');
    const lines = (await response.text()).trim().split('\n\n');
    assert.equal(lines.pop(), 'data: [DONE]');
    const chunks = lines.map(line => JSON.parse(line.slice(6)));
    assert.equal(chunks[1].choices[0].finish_reason, finish);
    const delta = chunks[0].choices[0].delta;
    if (index === 0) assert.equal(delta.content, 'Fixture complete');
    else {
      assert.equal(delta.tool_calls[0].function.name, 'read');
      assert.deepEqual(JSON.parse(delta.tool_calls[0].function.arguments), { path: 'SKILL.md' });
    }
    assert.deepEqual(requests[index], request);
  }
  assert.deepEqual(errors, []);
});
