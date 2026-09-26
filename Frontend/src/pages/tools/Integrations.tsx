import { useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Check, Copy, Eye, EyeOff, RefreshCw, ShieldOff } from 'lucide-react';
import { ModuleToolPage } from '@/components/tools/ModuleToolPage';
import { alert } from '@/lib/alert';
import { getConfig } from '@/services/configLoader';
import {
  createShopAdminIntegrationKey,
  getShopAdminIntegrationKeys,
  patchShopAdminIntegrationKey,
  type ShopAdminIntegrationKeyItem,
} from '@/services/shopAdmin';

type TabKey = 'public_api';

function formatDateTime(v: string | null | undefined) {
  if (!v) return '—';
  return v;
}

function base64UrlFromBytes(bytes: Uint8Array) {
  let binary = '';
  for (let i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i]);
  const base64 = btoa(binary);
  return base64.replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '');
}

function generateIntegrationKey() {
  const bytes = new Uint8Array(32);
  crypto.getRandomValues(bytes);
  return base64UrlFromBytes(bytes);
}

async function copyText(text: string) {
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
      return true;
    }
  } catch {
    // ignore and fallback
  }

  try {
    const el = document.createElement('textarea');
    el.value = text;
    el.setAttribute('readonly', '');
    el.style.position = 'fixed';
    el.style.top = '0';
    el.style.left = '0';
    el.style.opacity = '0';
    document.body.appendChild(el);
    el.focus();
    el.select();
    const ok = document.execCommand('copy');
    document.body.removeChild(el);
    return ok;
  } catch {
    return false;
  }
}

async function manualCopyPrompt({ title, value }: { title: string; value: string }) {
  await alert({
    icon: 'info',
    title,
    text: undefined,
    input: 'textarea',
    inputValue: value,
    confirmButtonText: 'OK',
    didOpen: () => {
      const input = document.querySelector('.swal2-textarea') as HTMLTextAreaElement | null;
      if (input) {
        input.focus();
        input.select();
      }
    },
  });
}

export default function Integrations() {
  const { t, i18n } = useTranslation();

  const [tab, setTab] = useState<TabKey>('public_api');

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [items, setItems] = useState<ShopAdminIntegrationKeyItem[]>([]);

  const [showSecret, setShowSecret] = useState(false);
  const [generatedSecret, setGeneratedSecret] = useState<string | null>(null);
  const [busyRotate, setBusyRotate] = useState(false);
  const [busyDisable, setBusyDisable] = useState(false);
  const [secretCopied, setSecretCopied] = useState(false);
  const [baseUrlCopied, setBaseUrlCopied] = useState(false);
  const [promptCopied, setPromptCopied] = useState(false);

  const discordItems = useMemo(() => items.filter((x) => x.name === 'discord-bot'), [items]);
  const activeDiscordKey = useMemo(() => discordItems.find((x) => x.enabled === 1) || null, [discordItems]);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const r = await getShopAdminIntegrationKeys();
      if (!r.success) {
        setError(r.error || r.message || t('common.error', { defaultValue: 'Error' }));
        return;
      }
      setItems(r.data.items || []);
    } catch (e: any) {
      setError(e?.message || t('common.error', { defaultValue: 'Error' }));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const onRotate = async () => {
    const secret = generateIntegrationKey();
    if (secret.length < 32) {
      await alert({
        icon: 'error',
        title: t('tools.integrations.discord.rotateErrorTitle', { defaultValue: 'Invalid key' }),
        text: t('tools.integrations.discord.rotateErrorText', { defaultValue: 'Generated key does not meet minimum length (32).' }),
      });
      return;
    }

    const confirm = await alert({
      icon: 'warning',
      title: t('tools.integrations.discord.rotateConfirmTitle', { defaultValue: 'Rotate key?' }),
      text: t('tools.integrations.discord.rotateConfirmText', {
        defaultValue: 'This will disable previous keys and create a new active key. You will only see the password once.',
      }),
      showCancelButton: true,
      confirmButtonText: t('tools.integrations.discord.rotateConfirmYes', { defaultValue: 'Rotate' }),
      cancelButtonText: t('common.cancel', { defaultValue: 'Cancel' }),
    });

    if (!confirm.isConfirmed) return;

    setBusyRotate(true);
    setGeneratedSecret(null);
    setShowSecret(false);
    try {
      const r = await createShopAdminIntegrationKey({ name: 'discord-bot', key: secret });
      if (!r.success) {
        await alert({
          icon: 'error',
          title: t('tools.integrations.discord.rotateFailedTitle', { defaultValue: 'Failed to rotate' }),
          text: r.error || r.message || t('common.error', { defaultValue: 'Error' }),
        });
        return;
      }

      setGeneratedSecret(secret);
      setShowSecret(true);

      await alert({
        icon: 'success',
        title: t('tools.integrations.discord.rotateSuccessTitle', { defaultValue: 'New key generated' }),
        text: t('tools.integrations.discord.rotateSuccessText', {
          defaultValue: 'Copy the password now. It will not be shown again.',
        }),
      });

      await load();
    } catch (e: any) {
      await alert({
        icon: 'error',
        title: t('tools.integrations.discord.rotateFailedTitle', { defaultValue: 'Failed to rotate' }),
        text: e?.message || t('common.error', { defaultValue: 'Error' }),
      });
    } finally {
      setBusyRotate(false);
    }
  };

  const onDisable = async () => {
    if (!activeDiscordKey) return;

    const confirm = await alert({
      icon: 'warning',
      title: t('tools.integrations.discord.disableConfirmTitle', { defaultValue: 'Disable key?' }),
      text: t('tools.integrations.discord.disableConfirmText', {
        defaultValue: 'This will disable the current key. The bot will stop working until you generate a new one.',
      }),
      showCancelButton: true,
      confirmButtonText: t('tools.integrations.discord.disableConfirmYes', { defaultValue: 'Disable' }),
      cancelButtonText: t('common.cancel', { defaultValue: 'Cancel' }),
    });

    if (!confirm.isConfirmed) return;

    setBusyDisable(true);
    try {
      const r = await patchShopAdminIntegrationKey(activeDiscordKey.key_id, { enabled: 0 });
      if (!r.success) {
        await alert({
          icon: 'error',
          title: t('tools.integrations.discord.disableFailedTitle', { defaultValue: 'Failed to disable' }),
          text: r.error || r.message || t('common.error', { defaultValue: 'Error' }),
        });
        return;
      }
      await load();
    } catch (e: any) {
      await alert({
        icon: 'error',
        title: t('tools.integrations.discord.disableFailedTitle', { defaultValue: 'Failed to disable' }),
        text: e?.message || t('common.error', { defaultValue: 'Error' }),
      });
    } finally {
      setBusyDisable(false);
    }
  };

  const [backendOrigin, setBackendOrigin] = useState<string>(window.location.origin);
  const [apiBasePath, setApiBasePath] = useState<string>('/api');

  useEffect(() => {
    const run = async () => {
      try {
        const cfg = await getConfig();
        const protocol = cfg?.backend?.protocol || 'http';
        const host = cfg?.backend?.host || 'localhost';
        const port = typeof cfg?.backend?.port === 'number' ? cfg.backend.port : 3000;
        const basePath = cfg?.backend?.basePath || '/api';

        setBackendOrigin(`${protocol}://${host}:${port}`);
        setApiBasePath(basePath.startsWith('/') ? basePath : `/${basePath}`);
      } catch {
        // keep defaults
      }
    };

    run();
  }, []);

  const apiBaseUrl = `${backendOrigin}${apiBasePath}`;

  const discordBotPrompt = useMemo(() => {
    const baseUrl = backendOrigin;
    const lang = (i18n.language || '').toLowerCase();
    const isPt = lang.startsWith('pt');

    if (isPt) {
      return `Voce e um desenvolvedor senior. Gere um BOT para Discord em PYTHON para administrar VIP e Wallet de um servidor SCUM usando uma API chamada SSM.

## Objetivo
Criar um bot Discord (Python) que execute comandos para:
- Consultar saldo da wallet
- Creditar wallet
- Debitar wallet
- Ativar VIP
- Desativar VIP

## Stack obrigatoria
- Python 3.10+
- discord.py
- requests (ou httpx)
- python-dotenv
- uuid (stdlib)

## Requisitos de seguranca (obrigatorios)
- NUNCA hardcode tokens/chaves no codigo.
- Ler segredos via variaveis de ambiente usando .env.
- Nunca imprimir/logar o DISCORD_BOT_TOKEN nem o SSM_INTEGRATION_KEY.
- Fornecer .env.example e instruir a criar .env localmente.

## Variaveis de ambiente obrigatorias
- DISCORD_BOT_TOKEN= (token do bot criado no Discord Developer Portal)
- SSM_INTEGRATION_KEY= (chave de integracao do painel do SSM; vai no header X-Integration-Key)
- BASE_URL= (ex: ${baseUrl})

## Endpoints disponiveis (todos sao POST e exigem header X-Integration-Key)
1) POST {BASE_URL}/api/integrations/wallet/balance
Body:
{
  "external_id": "...",
  "steam_id": "..."
}

2) POST {BASE_URL}/api/integrations/wallet/credit
Body:
{
  "external_id": "...",
  "steam_id": "...",
  "amount": 100,
  "meta": { "source": "discord-bot" }
}

3) POST {BASE_URL}/api/integrations/wallet/debit
Body:
{
  "external_id": "...",
  "steam_id": "...",
  "amount": 50,
  "meta": { "source": "discord-bot" }
}

4) POST {BASE_URL}/api/integrations/vip/activate
Body:
{
  "external_id": "...",
  "steam_id": "...",
  "meta": { "source": "discord-bot" }
}

5) POST {BASE_URL}/api/integrations/vip/deactivate
Body:
{
  "external_id": "...",
  "steam_id": "...",
  "meta": { "source": "discord-bot" }
}

## Regra CRITICA: Idempotencia via external_id
- external_id e obrigatorio em TODAS as requests.
- O bot deve gerar external_id UNICO por operacao usando UUID:
  ex: "discord:<acao>:<uuid>"
- Se houver retry do mesmo comando, pode reutilizar o mesmo external_id SOMENTE para aquele retry.
- Se external_id repetir em chamadas diferentes, o servidor pode retornar resposta antiga e NAO aplicar novamente.

## Regra CRITICA: Rate limit do wallet/balance
- O endpoint /wallet/balance pode ter rate limit (ex: 10 minutos por steam_id).
- Se receber HTTP 429, o bot deve responder ao usuario dizendo para tentar novamente apos X segundos (campo retry_after_seconds).
- Para confirmar credito/debito, confie no balance retornado pelo proprio credit/debit (se a API retornar), e evite ficar consultando balance em loop.

## Comandos do bot (prefix commands, MVP)
Use comandos com prefixo "!" (mais simples).
Comandos:
- !saldo <steam_id>
- !creditar <steam_id> <amount>
- !debitar <steam_id> <amount>
- !vipon <steam_id>
- !vipoff <steam_id>

Regras dos comandos:
- Validar steam_id nao vazio.
- amount deve ser inteiro > 0 para credit/debit.
- Responder mensagens claras em PT-BR.
- Em erro HTTP, mostrar status code e uma mensagem amigavel; incluir o "error" retornado no JSON se existir (ex: PLAYER_NOT_FOUND).
- Timeouts: 10s por request.
- Nao travar o loop do Discord: usar execucao assincrona adequada (loop executor ou httpx async, mas mantenha simples e funcionando).

## Entregaveis (arquivos)
Gere exatamente estes arquivos:
1) bot.py
2) requirements.txt
3) .env.example
4) README.md

## Conteudo obrigatorio do README.md
- Como criar o bot no Discord Developer Portal e obter DISCORD_BOT_TOKEN
- Como configurar .env com DISCORD_BOT_TOKEN, SSM_INTEGRATION_KEY e BASE_URL
- Como instalar dependencias (pip install -r requirements.txt)
- Como rodar (python bot.py)
- Exemplos de comandos

## Observacoes de qualidade
- Estruture o codigo com funcoes: build_headers(), post_json(), build_external_id(action)
- Centralize o BASE_URL e o header X-Integration-Key.
- Trate JSON invalido/sem resposta.
- O bot deve iniciar e conectar ao Discord sem exigir configuracoes extras alem do .env.

Agora gere os arquivos completos, prontos para uso.`;
    }

    return `You are a senior developer. Generate a Discord BOT in PYTHON to manage VIP and Wallet for a SCUM server using an API called SSM.

## Goal
Create a Discord bot (Python) that can run commands to:
- Check wallet balance
- Credit wallet
- Debit wallet
- Activate VIP
- Deactivate VIP

## Required stack
- Python 3.10+
- discord.py
- requests (or httpx)
- python-dotenv
- uuid (stdlib)

## Security requirements (mandatory)
- NEVER hardcode tokens/keys in the source code.
- Read secrets from environment variables using a .env file.
- Never print/log DISCORD_BOT_TOKEN nor SSM_INTEGRATION_KEY.
- Provide a .env.example file and instruct the user to create a local .env.

## Required environment variables
- DISCORD_BOT_TOKEN= (bot token created in Discord Developer Portal)
- SSM_INTEGRATION_KEY= (integration key generated in the SSM panel; sent in X-Integration-Key header)
- BASE_URL= (e.g. ${baseUrl})

## Available endpoints (all are POST and require X-Integration-Key header)
1) POST {BASE_URL}/api/integrations/wallet/balance
Body:
{
  "external_id": "...",
  "steam_id": "..."
}

2) POST {BASE_URL}/api/integrations/wallet/credit
Body:
{
  "external_id": "...",
  "steam_id": "...",
  "amount": 100,
  "meta": { "source": "discord-bot" }
}

3) POST {BASE_URL}/api/integrations/wallet/debit
Body:
{
  "external_id": "...",
  "steam_id": "...",
  "amount": 50,
  "meta": { "source": "discord-bot" }
}

4) POST {BASE_URL}/api/integrations/vip/activate
Body:
{
  "external_id": "...",
  "steam_id": "...",
  "meta": { "source": "discord-bot" }
}

5) POST {BASE_URL}/api/integrations/vip/deactivate
Body:
{
  "external_id": "...",
  "steam_id": "...",
  "meta": { "source": "discord-bot" }
}

## CRITICAL rule: Idempotency via external_id
- external_id is required in ALL requests.
- The bot must generate a UNIQUE external_id per operation using UUID:
  e.g. "discord:<action>:<uuid>"
- If the same command is retried, you may reuse the same external_id ONLY for that retry.
- If external_id is reused across different calls, the server may return a previous response and NOT apply it again.

## CRITICAL rule: wallet/balance rate limit
- The /wallet/balance endpoint can be rate limited (e.g. 10 minutes per steam_id).
- If HTTP 429 is returned, the bot should tell the user to try again after X seconds (retry_after_seconds).
- To confirm credit/debit, rely on the balance returned by credit/debit (if the API returns it), and avoid polling balance in a loop.

## Bot commands (prefix commands, MVP)
Use commands with the "!" prefix (simpler).
Commands:
- !saldo <steam_id>
- !creditar <steam_id> <amount>
- !debitar <steam_id> <amount>
- !vipon <steam_id>
- !vipoff <steam_id>

Command rules:
- Validate steam_id is not empty.
- amount must be an integer > 0 for credit/debit.
- Reply with clear messages.
- On HTTP errors, show the status code and a friendly message; include the "error" field from the JSON if present (e.g. PLAYER_NOT_FOUND).
- Timeouts: 10s per request.
- Do not block the Discord loop: use proper async execution (loop executor or httpx async), but keep it simple and working.

## Deliverables (files)
Generate exactly these files:
1) bot.py
2) requirements.txt
3) .env.example
4) README.md

## README.md mandatory content
- How to create a bot in Discord Developer Portal and get DISCORD_BOT_TOKEN
- How to configure .env with DISCORD_BOT_TOKEN, SSM_INTEGRATION_KEY and BASE_URL
- How to install dependencies (pip install -r requirements.txt)
- How to run (python bot.py)
- Command examples

## Quality notes
- Structure the code with functions: build_headers(), post_json(), build_external_id(action)
- Centralize BASE_URL and the X-Integration-Key header.
- Handle invalid JSON/no response.
- The bot must start and connect to Discord without requiring extra setup besides the .env.

Now generate the complete files, ready to use.`;
  }, [backendOrigin, i18n.language]);

  return (
    <ModuleToolPage
      title={t('tools.integrations.title', { defaultValue: 'Integrações' })}
      subtitle={t('tools.integrations.subtitle', {
        defaultValue: 'Manage public integrations (API keys) for external bots/systems.',
      })}
    >
      <div className="card p-4">
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setTab('public_api')}
            className={
              tab === 'public_api'
                ? 'px-3 py-2 rounded-lg border border-scum-orange/60 bg-scum-orange/10 text-sm font-semibold text-scum-orange'
                : 'px-3 py-2 rounded-lg border border-white/15 bg-white/8 text-sm font-medium text-white/90 hover:bg-white/12 hover:border-white/25'
            }
          >
            {t('tools.integrations.tabs.publicApi', { defaultValue: 'API Pública' })}
          </button>

          <button
            type="button"
            disabled={loading}
            onClick={load}
            className="ml-auto px-3 py-2 rounded-lg border border-white/15 bg-white/8 text-sm font-medium text-white/90 shadow-sm hover:text-white hover:bg-white/12 hover:border-white/25 focus:outline-none focus:ring-2 focus:ring-scum-orange/70 disabled:opacity-70 disabled:cursor-not-allowed"
          >
            <span className="inline-flex items-center gap-2">
              <RefreshCw size={16} />
              {t('common.refresh', { defaultValue: 'Refresh' })}
            </span>
          </button>
        </div>

        {error && <div className="mt-3 text-sm text-red-400">{error}</div>}
      </div>

      {tab === 'public_api' && (
        <div className="grid grid-cols-1 xl:grid-cols-[420px_1fr] gap-4">
          <div className="card p-4 space-y-4">
            <div className="text-sm font-semibold">
              {t('tools.integrations.discord.title', { defaultValue: 'Discord Bot' })}
            </div>

            <div className="space-y-2">
              <div className="text-xs uppercase text-white/40">
                {t('tools.integrations.status.title', { defaultValue: 'Status' })}
              </div>
              <div className="text-sm text-white/80">
                {t('tools.integrations.status.active', { defaultValue: 'Active key:' })}{' '}
                <span className={activeDiscordKey ? 'text-green-300' : 'text-white/50'}>
                  {activeDiscordKey ? 'ON' : 'OFF'}
                </span>
              </div>
              <div className="text-sm text-white/80">
                {t('tools.integrations.status.createdAt', { defaultValue: 'Created at:' })}{' '}
                <span className="text-white/60">{formatDateTime(activeDiscordKey?.created_at)}</span>
              </div>
              <div className="text-sm text-white/80">
                {t('tools.integrations.status.lastUsedAt', { defaultValue: 'Last used:' })}{' '}
                <span className="text-white/60">{formatDateTime(activeDiscordKey?.last_used_at)}</span>
              </div>
            </div>

            <div className="pt-3 border-t border-white/10" />

            <div className="space-y-2">
              <div className="text-xs uppercase text-white/40">
                {t('tools.integrations.actions.title', { defaultValue: 'Actions' })}
              </div>

              <button
                disabled={busyRotate}
                onClick={onRotate}
                className="w-full px-3 py-2 rounded-lg border border-scum-orange/60 bg-scum-orange/10 text-sm font-semibold text-scum-orange shadow-sm hover:bg-scum-orange/20 hover:border-scum-orange/80 focus:outline-none focus:ring-2 focus:ring-scum-orange/70 disabled:opacity-70 disabled:cursor-not-allowed"
              >
                <span className="inline-flex items-center gap-2">
                  <RefreshCw size={16} />
                  {t('tools.integrations.discord.rotate', { defaultValue: 'Generate new password (rotate)' })}
                </span>
              </button>

              <button
                disabled={!activeDiscordKey || busyDisable}
                onClick={onDisable}
                className="w-full px-3 py-2 rounded-lg border border-red-500/40 bg-red-500/10 text-sm font-semibold text-red-300 shadow-sm hover:bg-red-500/20 hover:border-red-500/70 focus:outline-none focus:ring-2 focus:ring-red-500/30 disabled:opacity-70 disabled:cursor-not-allowed"
              >
                <span className="inline-flex items-center gap-2">
                  <ShieldOff size={16} />
                  {t('tools.integrations.discord.disable', { defaultValue: 'Disable current key' })}
                </span>
              </button>

              <div className="text-xs text-white/50">
                {t('tools.integrations.discord.secretNotice', {
                  defaultValue: 'The password will only be shown once. Save it in a secure place.',
                })}
              </div>
            </div>

            {generatedSecret && (
              <div className="pt-3 border-t border-white/10 space-y-2">
                <div className="text-xs uppercase text-white/40">
                  {t('tools.integrations.discord.newKey', { defaultValue: 'New password' })}
                </div>

                <div className="flex items-center gap-2">
                  <input
                    readOnly
                    value={showSecret ? generatedSecret : '•'.repeat(Math.max(16, generatedSecret.length))}
                    className="min-w-0 flex-1 px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-white text-sm focus:outline-none"
                  />
                  <button
                    type="button"
                    onClick={() => setShowSecret((v) => !v)}
                    className="p-2 rounded-lg border border-white/15 bg-white/8 text-white/90 hover:text-white hover:bg-white/12 hover:border-white/25"
                    title={t('tools.integrations.discord.toggleVisibility', { defaultValue: 'Show/hide' })}
                  >
                    {showSecret ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                  <button
                    type="button"
                    onClick={async () => {
                      const ok = await copyText(generatedSecret);
                      if (!ok) {
                        await manualCopyPrompt({
                          title: t('tools.integrations.discord.copyFailedTitle', { defaultValue: 'Copy failed' }),
                          value: generatedSecret,
                        });
                        return;
                      }

                      setSecretCopied(true);
                      window.setTimeout(() => setSecretCopied(false), 1500);
                    }}
                    className="p-2 rounded-lg border border-white/15 bg-white/8 text-white/90 hover:text-white hover:bg-white/12 hover:border-white/25"
                    title={
                      secretCopied
                        ? t('tools.integrations.discord.copied', { defaultValue: 'Copied!' })
                        : t('tools.integrations.discord.copy', { defaultValue: 'Copy' })
                    }
                  >
                    {secretCopied ? <Check size={16} /> : <Copy size={16} />}
                  </button>
                </div>

                <button
                  type="button"
                  onClick={() => {
                    setGeneratedSecret(null);
                    setShowSecret(false);
                  }}
                  className="w-full px-3 py-2 rounded-lg border border-white/15 bg-white/8 text-sm font-medium text-white/90 hover:bg-white/12 hover:border-white/25"
                >
                  {t('tools.integrations.discord.clearSecret', { defaultValue: 'Hide and clear' })}
                </button>
              </div>
            )}

            {discordItems.length > 0 && (
              <div className="pt-3 border-t border-white/10 space-y-2">
                <div className="text-xs uppercase text-white/40">
                  {t('tools.integrations.discord.history', { defaultValue: 'History' })}
                </div>
                <div className="space-y-2">
                  {discordItems
                    .slice()
                    .sort((a, b) => (a.created_at < b.created_at ? 1 : -1))
                    .slice(0, 5)
                    .map((k) => (
                      <div key={k.key_id} className="text-xs text-white/60 flex items-center justify-between gap-2">
                        <div className="truncate">{k.key_id}</div>
                        <div className={k.enabled ? 'text-green-300' : 'text-white/40'}>{k.enabled ? 'ON' : 'OFF'}</div>
                      </div>
                    ))}
                </div>
              </div>
            )}
          </div>

          <div className="card p-4 space-y-4">
            <div className="text-sm font-semibold">
              {t('tools.integrations.publicApi.title', { defaultValue: 'API Pública' })}
            </div>

            <div className="text-sm text-white/70">
              {t('tools.integrations.publicApi.help', {
                defaultValue:
                  'These endpoints are used by external bots/systems. They require the X-Integration-Key header (the generated password).',
              })}
            </div>

            <div className="space-y-2">
              <div className="text-xs uppercase text-white/40">
                {t('tools.integrations.publicApi.baseUrl', { defaultValue: 'Base URL' })}
              </div>
              <div className="flex items-center gap-2">
                <input
                  readOnly
                  value={backendOrigin}
                  className="min-w-0 flex-1 px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-white text-sm focus:outline-none"
                />
                <button
                  type="button"
                  onClick={async () => {
                    const ok = await copyText(backendOrigin);
                    if (!ok) {
                      await manualCopyPrompt({
                        title: t('tools.integrations.discord.copyFailedTitle', { defaultValue: 'Copy failed' }),
                        value: backendOrigin,
                      });
                      return;
                    }

                    setBaseUrlCopied(true);
                    window.setTimeout(() => setBaseUrlCopied(false), 1500);
                  }}
                  className="p-2 rounded-lg border border-white/15 bg-white/8 text-white/90 hover:text-white hover:bg-white/12 hover:border-white/25"
                  title={
                    baseUrlCopied
                      ? t('tools.integrations.discord.copied', { defaultValue: 'Copied!' })
                      : t('tools.integrations.discord.copy', { defaultValue: 'Copy' })
                  }
                >
                  {baseUrlCopied ? <Check size={16} /> : <Copy size={16} />}
                </button>
              </div>
            </div>

            <div className="pt-3 border-t border-white/10" />

            <div className="space-y-3">
              <div className="text-xs uppercase text-white/40">
                {t('tools.integrations.publicApi.botPrompt.title', { defaultValue: 'Discord Bot (Python)' })}
              </div>

              <div className="text-sm text-white/70">
                <div>{t('tools.integrations.publicApi.botPrompt.step1', { defaultValue: '1) You need DISCORD_BOT_TOKEN (Discord Developer Portal)' })}</div>
                <div>{t('tools.integrations.publicApi.botPrompt.step2', { defaultValue: '2) You need X-Integration-Key (generated here in the panel)' })}</div>
                <div>{t('tools.integrations.publicApi.botPrompt.step3', { defaultValue: '3) Configure .env and run the bot' })}</div>
              </div>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={async () => {
                    const ok = await copyText(discordBotPrompt);
                    if (!ok) {
                      await manualCopyPrompt({
                        title: t('tools.integrations.publicApi.botPrompt.copyTitle', { defaultValue: 'Copy prompt (Discord / Python)' }),
                        value: discordBotPrompt,
                      });
                      return;
                    }

                    setPromptCopied(true);
                    window.setTimeout(() => setPromptCopied(false), 1500);
                  }}
                  className="px-3 py-2 rounded-lg border border-white/15 bg-white/8 text-sm font-medium text-white/90 hover:bg-white/12 hover:border-white/25"
                >
                  <span className="inline-flex items-center gap-2">
                    {promptCopied ? <Check size={16} /> : <Copy size={16} />}
                    {promptCopied
                      ? t('tools.integrations.publicApi.botPrompt.copied', { defaultValue: 'Copied!' })
                      : t('tools.integrations.publicApi.botPrompt.copyButton', { defaultValue: 'Copy prompt (Discord / Python)' })}
                  </span>
                </button>
              </div>

              <details className="rounded-lg border border-white/10 bg-black/20">
                <summary className="cursor-pointer select-none px-3 py-2 text-xs text-white/70 hover:text-white">
                  {t('tools.integrations.publicApi.botPrompt.view', { defaultValue: 'View prompt' })}
                </summary>
                <div className="px-3 pb-3">
                  <pre className="text-xs bg-black/30 border border-white/10 rounded-lg p-3 overflow-auto whitespace-pre-wrap">
{discordBotPrompt}</pre>
                </div>
              </details>
            </div>

            <div className="space-y-3">
              <div className="text-xs uppercase text-white/40">
                {t('tools.integrations.publicApi.examples', { defaultValue: 'Examples' })}
              </div>

              <div className="space-y-2">
                <details className="rounded-lg border border-white/10 bg-black/20">
                  <summary className="cursor-pointer select-none px-3 py-2 text-xs text-white/70 hover:text-white">
                    {t('tools.integrations.publicApi.endpoints.walletCredit', { defaultValue: 'Wallet credit' })}
                  </summary>
                  <div className="px-3 pb-3">
                    <pre className="text-xs bg-black/30 border border-white/10 rounded-lg p-3 overflow-auto">
{`POST ${apiBaseUrl}/integrations/wallet/credit\nX-Integration-Key: <PASSWORD>\n\n{\n  \"external_id\": \"discord:credit:123\",\n  \"steam_id\": \"76561198012345678\",\n  \"amount\": 100,\n  \"meta\": { \"source\": \"discord\" }\n}`}</pre>
                  </div>
                </details>

                <details className="rounded-lg border border-white/10 bg-black/20">
                  <summary className="cursor-pointer select-none px-3 py-2 text-xs text-white/70 hover:text-white">
                    {t('tools.integrations.publicApi.endpoints.walletDebit', { defaultValue: 'Wallet debit' })}
                  </summary>
                  <div className="px-3 pb-3">
                    <pre className="text-xs bg-black/30 border border-white/10 rounded-lg p-3 overflow-auto">
{`POST ${apiBaseUrl}/integrations/wallet/debit\nX-Integration-Key: <PASSWORD>\n\n{\n  \"external_id\": \"discord:debit:123\",\n  \"steam_id\": \"76561198012345678\",\n  \"amount\": 50,\n  \"meta\": { \"source\": \"discord\" }\n}`}</pre>
                  </div>
                </details>

                <details className="rounded-lg border border-white/10 bg-black/20">
                  <summary className="cursor-pointer select-none px-3 py-2 text-xs text-white/70 hover:text-white">
                    {t('tools.integrations.publicApi.endpoints.walletBalance', { defaultValue: 'Wallet balance (read-only)' })}
                  </summary>
                  <div className="px-3 pb-3 space-y-2">
                    <div className="text-xs text-white/50">
                      {t('tools.integrations.publicApi.endpoints.walletBalanceRateLimit', {
                        defaultValue: 'Rate limit: 10 minutes per (integration key, steam_id).',
                      })}
                    </div>
                    <div className="text-xs text-white/50">
                      {t('tools.integrations.publicApi.endpoints.walletBalanceResponseIncludes', {
                        defaultValue: 'Response includes: player_name, balance.',
                      })}
                    </div>
                    <pre className="text-xs bg-black/30 border border-white/10 rounded-lg p-3 overflow-auto">
{`POST ${apiBaseUrl}/integrations/wallet/balance\nX-Integration-Key: <PASSWORD>\n\n{\n  \"external_id\": \"discord:balance:123\",\n  \"steam_id\": \"76561198012345678\",\n  \"meta\": { \"source\": \"discord\" }\n}`}</pre>
                  </div>
                </details>

                <details className="rounded-lg border border-white/10 bg-black/20">
                  <summary className="cursor-pointer select-none px-3 py-2 text-xs text-white/70 hover:text-white">
                    {t('tools.integrations.publicApi.endpoints.vipActivate', { defaultValue: 'VIP activate' })}
                  </summary>
                  <div className="px-3 pb-3">
                    <pre className="text-xs bg-black/30 border border-white/10 rounded-lg p-3 overflow-auto">
{`POST ${apiBaseUrl}/integrations/vip/activate\nX-Integration-Key: <PASSWORD>\n\n{\n  \"external_id\": \"discord:vip_on:123\",\n  \"steam_id\": \"76561198012345678\",\n  \"meta\": { \"source\": \"discord\" }\n}`}</pre>
                  </div>
                </details>

                <details className="rounded-lg border border-white/10 bg-black/20">
                  <summary className="cursor-pointer select-none px-3 py-2 text-xs text-white/70 hover:text-white">
                    {t('tools.integrations.publicApi.endpoints.vipDeactivate', { defaultValue: 'VIP deactivate' })}
                  </summary>
                  <div className="px-3 pb-3">
                    <pre className="text-xs bg-black/30 border border-white/10 rounded-lg p-3 overflow-auto">
{`POST ${apiBaseUrl}/integrations/vip/deactivate\nX-Integration-Key: <PASSWORD>\n\n{\n  \"external_id\": \"discord:vip_off:123\",\n  \"steam_id\": \"76561198012345678\",\n  \"meta\": { \"source\": \"discord\" }\n}`}</pre>
                  </div>
                </details>
              </div>
            </div>
          </div>
        </div>
      )}
    </ModuleToolPage>
  );
}
