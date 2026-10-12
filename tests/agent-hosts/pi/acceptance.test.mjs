// Real Pi discovery, prompt expansion and read-tool loop; scripted model transport.
import assert from 'node:assert/strict';
import { cp, mkdir, mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import { createServer } from 'node:http';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { after, test } from 'node:test';

const root = fileURLToPath(new URL('../../../', import.meta.url));
const home = await mkdtemp(join(tmpdir(), 'skills-pi-'));
// Import only after isolating the profile and removing inherited provider credentials.
const keep = new Set(['PATH', 'SystemRoot', 'SYSTEMROOT', 'COMSPEC', 'PATHEXT', 'TEMP', 'TMP', 'NODE_TEST_CONTEXT']);
for (const key of Object.keys(process.env)) if (!keep.has(key)) delete process.env[key];
Object.assign(process.env, { HOME: home, USERPROFILE: home, PI_CODING_AGENT_DIR: join(home, '.pi/agent'),
  XDG_CONFIG_HOME: join(home, '.config'), XDG_CACHE_HOME: join(home, '.cache'),
  DO_NOT_TRACK: '1', NO_PROXY: '127.0.0.1,localhost' });
const { createAgentSession, DefaultResourceLoader, ModelRuntime, SessionManager, SettingsManager } =
  await import('@earendil-works/pi-coding-agent');
after(() => rm(home, { recursive: true, force: true }));
const names = ['conventional-commit-batcher', 'dev-jev', 'qdrant-memory',
  'repository-quality-gate-fixer', 'sonarcloud-link-inspector'];

async function fixture(t, scope = 'project', selected = names) {
  const directory = await mkdtemp(join(home, 'case-'));
  const cwd = join(directory, 'project');
  const agentDir = join(directory, 'agent');
  const installed = scope === 'project' ? join(cwd, '.pi/skills') : join(agentDir, 'skills');
  await mkdir(installed, { recursive: true });
  await mkdir(cwd, { recursive: true });
  await mkdir(agentDir, { recursive: true });
  for (const name of selected) await cp(join(root, name), join(installed, name), { recursive: true });
  const settingsManager = SettingsManager.inMemory({ compaction: { enabled: false }, retry: { enabled: false } });
  const loader = new DefaultResourceLoader({ cwd, agentDir, settingsManager,
    noExtensions: true, noPromptTemplates: true, noThemes: true, noContextFiles: true });
  await loader.reload();
  t.after(() => rm(directory, { recursive: true, force: true }));
  return { cwd, agentDir, installed, settingsManager, loader };
}

for (const scope of ['project', 'global']) {
  test(`Pi discovers the exact five-package catalog in ${scope} scope`, async (t) => {
    const { loader, installed } = await fixture(t, scope);
    const discovered = loader.getSkills();
    assert.deepEqual(discovered.diagnostics, []);
    assert.deepEqual(discovered.skills.map(s => s.name).sort(), names);
    for (const skill of discovered.skills) {
      assert.equal(skill.filePath, join(installed, skill.name, 'SKILL.md'));
      assert.ok(skill.description.length > 0);
      assert.equal(skill.disableModelInvocation, false);
    }
  });
}

test('Pi loads a singleton without sibling skill dependencies', async (t) => {
  const { loader } = await fixture(t, 'project', ['qdrant-memory']);
  assert.deepEqual(loader.getSkills().skills.map(s => s.name), ['qdrant-memory']);
  assert.deepEqual(loader.getSkills().diagnostics, []);
});

async function agent(t, files, replies) {
  const requests = [];
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
      res.writeHead(500);
      res.end(String(error));
    }
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  t.after(() => new Promise(resolve => { server.close(resolve); server.closeAllConnections(); }));
  const runtime = await ModelRuntime.create({ authPath: join(files.agentDir, 'auth.json'),
    modelsPath: null, modelsStorePath: join(files.agentDir, 'models-cache.json'),
    allowModelNetwork: false, refreshOnCreate: false });
  runtime.registerProvider('skills-ci', { api: 'openai-completions',
    baseUrl: `http://127.0.0.1:${server.address().port}/v1`, apiKey: 'synthetic-ci-placeholder', authHeader: false,
    models: [{ id: 'ci-fixture', name: 'CI fixture', reasoning: false, input: ['text'],
      contextWindow: 100000, maxTokens: 2000, cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 } }] });
  const { session } = await createAgentSession({ cwd: files.cwd, agentDir: files.agentDir,
    modelRuntime: runtime, model: runtime.getModel('skills-ci', 'ci-fixture'), thinkingLevel: 'off',
    resourceLoader: files.loader, settingsManager: files.settingsManager,
    sessionManager: SessionManager.inMemory(files.cwd), tools: ['read'] });
  t.after(() => session.dispose());
  return { session, requests };
}

function body(text) {
  // Pi normalizes Windows CRLF before stripping frontmatter and expanding skills.
  return text.replace(/\r\n?/g, '\n').replace(/^---\n[\s\S]*?\n---\n/, '').trim();
}
for (const name of names) {
  test(`Pi /skill:${name} expands CRLF installed instructions`, { timeout: 30000 }, async (t) => {
    const files = await fixture(t);
    const entrypoint = join(files.installed, name, 'SKILL.md');
    await writeFile(entrypoint, (await readFile(entrypoint, 'utf8')).replace(/\r?\n/g, '\r\n'));
    const { session, requests } = await agent(t, files, ['Fixture complete']);
    assert.deepEqual(session.getActiveToolNames(), ['read']);
    assert.ok(session.systemPrompt.includes(`<name>${name}</name>`));
    await session.prompt(`/skill:${name} Confirm instructions were loaded.`);
    assert.equal(requests.length, 1);
    const content = JSON.stringify(requests[0].messages);
    const expected = body(await readFile(entrypoint, 'utf8'));
    assert.ok(content.includes(JSON.stringify(expected).slice(1, -1)));
    assert.equal(session.getLastAssistantText(), 'Fixture complete');
  });
}

for (const workflow of ['usage', 'maintenance', 'migration']) {
  test(`Pi reads Qdrant entrypoint and ${workflow} reference through its real tool`, { timeout: 30000 }, async (t) => {
    const files = await fixture(t, 'project', ['qdrant-memory']);
    const entrypoint = join(files.installed, 'qdrant-memory/SKILL.md');
    const reference = join(files.installed, `qdrant-memory/references/${workflow}.md`);
    const { session, requests } = await agent(t, files, [{ path: entrypoint }, { path: reference }, 'Fixture complete']);
    // Progressive disclosure: catalog metadata goes in the system prompt, not full workflows.
    assert.ok(session.systemPrompt.includes('<name>qdrant-memory</name>'));
    assert.ok(!session.systemPrompt.includes('## Shared boundaries'));
    await session.prompt(`Read the qdrant-memory skill and its ${workflow} workflow.`);
    assert.equal(requests.length, 3);
    const toolResults = requests[2].messages.filter(m => m.role === 'tool');
    assert.equal(toolResults.length, 2);
    assert.ok(JSON.stringify(toolResults[0]).includes('## Shared boundaries'));
    const expected = (await readFile(reference, 'utf8')).trim();
    assert.ok(JSON.stringify(toolResults[1]).includes(JSON.stringify(expected).slice(1, -1)));
    assert.equal(session.getLastAssistantText(), 'Fixture complete');
    assert.deepEqual(session.getActiveToolNames(), ['read']);
  });
}
