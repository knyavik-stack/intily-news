const CRON = '*/5 * * * *';
const VERSION = '6.0';

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (url.pathname === '/health' && request.method === 'GET') {
      return Response.json({
        ok: true,
        service: 'intily-ai-news',
        version: VERSION,
        cron: CRON,
        scheduler: 'cloudflare-cron -> github-workflow-dispatch',
        time: new Date().toISOString()
      });
    }

    return new Response('Not found', { status: 404 });
  },

  async scheduled(event, env, ctx) {
    if (event.cron !== CRON) {
      console.log('CRON_IGNORED', event.cron);
      return;
    }

    ctx.waitUntil(dispatchGitHub(env));
  }
};

async function dispatchGitHub(env) {
  if (!env.GITHUB_DISPATCH_TOKEN) {
    throw new Error('GITHUB_DISPATCH_TOKEN_MISSING');
  }

  const response = await fetch(
    'https://api.github.com/repos/knyavik-stack/intily-news/actions/workflows/intily-ai-news.yml/dispatches',
    {
      method: 'POST',
      headers: {
        authorization: `Bearer ${env.GITHUB_DISPATCH_TOKEN}`,
        accept: 'application/vnd.github+json',
        'content-type': 'application/json',
        'user-agent': 'intily-cloudflare-scheduler/6.0'
      },
      body: JSON.stringify({ ref: 'main' })
    }
  );

  if (!response.ok) {
    const detail = await response.text().catch(() => '');
    throw new Error(
      `GITHUB_DISPATCH_FAILED ${response.status}: ${detail.slice(0, 300)}`
    );
  }

  console.log('GITHUB_DISPATCH', response.status, 'ref=main');
}
