import assert from 'node:assert/strict';
import { createServer } from 'node:http';

// Keep fixture failures in the test process, never in the HTTP response.
export function createModelServer(replies) {
  const requests = [];
  const errors = [];
  const server = createServer(async (req, res) => {
    try {
      assert.equal(req.url, '/v1/chat/completions');
      let text = '';
      for await (const chunk of req) text += chunk;
      const request = JSON.parse(text);
      assert.equal(request.stream, true);
      assert.equal(request.model, 'ci-fixture');
      const index = requests.push(request) - 1;
      assert.ok(index < replies.length, 'Unexpected model request or retry');
      const reply = replies[index];
      const delta = typeof reply === 'string' ? { role: 'assistant', content: reply } : {
        role: 'assistant', tool_calls: [{ index: 0, id: `call_${index}`, type: 'function',
          function: { name: 'read', arguments: JSON.stringify({ path: reply.path }) } }] };
      res.writeHead(200, { 'Content-Type': 'text/event-stream' });
      for (const [content, finish_reason] of [[delta, null], [{}, typeof reply === 'string' ? 'stop' : 'tool_calls']]) {
        res.write(`data: ${JSON.stringify({ id: `ci_${index}`, object: 'chat.completion.chunk',
          created: 0, model: 'ci-fixture', choices: [{ index: 0, delta: content, finish_reason }] })}\n\n`);
      }
      res.end('data: [DONE]\n\n');
    } catch (error) {
      errors.push(error);
      res.writeHead(500);
      res.end('Fixture model request failed');
    }
  });
  return { server, requests, errors };
}
