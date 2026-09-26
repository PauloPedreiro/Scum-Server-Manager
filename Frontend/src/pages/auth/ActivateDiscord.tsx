import { motion } from 'framer-motion';
import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link2, Loader2, Copy, CheckCircle2, AlertCircle } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

import SsmLogo from '@/assets/logo/SSMlogo1.png';
import backgroundImage from '@/assets/backgrounds/2421905-1920x1200-desktop-hd-scum-game-wallpaper-photo.jpg';
import { authService } from '@/services/auth';

type LinkCodeData = {
  code: string;
  expires_in_minutes: number;
  command: string;
};

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

export default function ActivateDiscord() {
  const { t } = useTranslation();
  const tEn = (key: string, options?: any): string => t(key, { ...options, lng: 'en' }) as string;
  const navigate = useNavigate();

  const [isChecking, setIsChecking] = useState(true);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isPolling, setIsPolling] = useState(false);
  const [linkData, setLinkData] = useState<LinkCodeData | null>(null);
  const [error, setError] = useState<string>('');
  const [copied, setCopied] = useState(false);

  const didAutoGenerateRef = useRef(false);

  const intervalRef = useRef<number | null>(null);
  const timeoutRef = useRef<number | null>(null);
  const copiedTimeoutRef = useRef<number | null>(null);

  const clearTimers = () => {
    if (intervalRef.current) {
      window.clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    if (timeoutRef.current) {
      window.clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
    if (copiedTimeoutRef.current) {
      window.clearTimeout(copiedTimeoutRef.current);
      copiedTimeoutRef.current = null;
    }
  };

  const flashCopied = () => {
    setCopied(true);
    if (copiedTimeoutRef.current) window.clearTimeout(copiedTimeoutRef.current);
    copiedTimeoutRef.current = window.setTimeout(() => {
      setCopied(false);
      copiedTimeoutRef.current = null;
    }, 2000);
  };

  const startPolling = () => {
    clearTimers();
    setIsPolling(true);

    intervalRef.current = window.setInterval(async () => {
      const me = await authService.getCurrentUser();
      if (!me) return;
      if (!authService.mustLinkDiscordFromUser(me)) {
        clearTimers();
        setIsPolling(false);
        navigate('/');
      }
    }, 2500);

    timeoutRef.current = window.setTimeout(() => {
      clearTimers();
      setIsPolling(false);
      setError(tEn('auth.activateDiscord.timeout'));
    }, 60000);
  };

  const generateCode = async (options?: { auto?: boolean }) => {
    const auto = options?.auto === true;
    setError('');
    setIsGenerating(true);
    try {
      const res = await authService.generateDiscordLinkCode();
      if (!res.success || !res.data) {
        setError(res.error || tEn('auth.activateDiscord.errors.generateFailed'));
        return;
      }

      setLinkData(res.data);
      startPolling();

      const ok = await copyText(res.data.command);
      if (ok && !auto) flashCopied();
    } finally {
      setIsGenerating(false);
    }
  };

  const handleGenerateCode = async () => {
    await generateCode();
  };

  const handleCopy = async () => {
    if (!linkData?.command) return;
    const ok = await copyText(linkData.command);
    if (ok) {
      flashCopied();
    } else {
      setError(tEn('auth.activateDiscord.errors.copyFailed'));
    }
  };

  useEffect(() => {
    const run = async () => {
      setIsChecking(true);
      const token = authService.getToken();
      if (!token) {
        navigate('/login', { replace: true });
        return;
      }

      const me = await authService.getCurrentUser();
      if (!me) {
        navigate('/login', { replace: true });
        return;
      }

      if (!authService.mustLinkDiscordFromUser(me)) {
        navigate('/', { replace: true });
        return;
      }

      setIsChecking(false);

      if (!didAutoGenerateRef.current) {
        didAutoGenerateRef.current = true;
        await generateCode({ auto: true });
      }
    };

    run();

    return () => {
      clearTimers();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="min-h-screen flex items-center justify-center p-4 relative overflow-hidden">
      <div className="absolute inset-0 bg-scum-bg">
        <motion.div
          initial={{ opacity: 0, scale: 1.1 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 1.5, ease: 'easeOut' }}
          className="absolute inset-0"
        >
          <img
            src={backgroundImage}
            alt=""
            className="w-full h-full object-cover md:object-center object-left"
            style={{ filter: 'blur(2px)' }}
          />
          <div className="absolute inset-0 bg-gradient-to-b from-black/60 via-black/50 to-black/70" />
        </motion.div>
      </div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="relative w-full max-w-md"
      >
        <div className="bg-black/40 backdrop-blur-md border border-white/10 rounded-2xl p-8 shadow-2xl">
          <div className="flex flex-col items-center gap-4 mb-6">
            <img src={SsmLogo} alt="SSM" className="h-16 w-auto" />
            <div className="text-center">
              <h1 className="text-2xl font-bold text-white">{tEn('auth.activateDiscord.title')}</h1>
              <p className="text-white/70 mt-2">{tEn('auth.activateDiscord.subtitle')}</p>
            </div>
          </div>

          {isChecking ? (
            <div className="flex items-center justify-center gap-3 text-white/80">
              <Loader2 className="h-5 w-5 animate-spin" />
              <span>{tEn('auth.activateDiscord.checking')}</span>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="flex items-start gap-3 text-white/80">
                <Link2 className="h-5 w-5 mt-0.5" />
                <div className="text-sm leading-6">
                  <div>{tEn('auth.activateDiscord.instructions.line1')}</div>
                  <div>
                    {tEn('auth.activateDiscord.instructions.line2').includes('#log-ssm') ? (
                      <>
                        {tEn('auth.activateDiscord.instructions.line2').split('#log-ssm')[0]}
                        <span className="inline-block text-scum-orange font-bold bg-scum-orange/10 px-1.5 py-0.5 rounded border border-scum-orange/20">
                          #log-ssm
                        </span>
                        {tEn('auth.activateDiscord.instructions.line2').split('#log-ssm')[1]}
                      </>
                    ) : (
                      tEn('auth.activateDiscord.instructions.line2')
                    )}
                  </div>
                  <div>{tEn('auth.activateDiscord.instructions.line3')}</div>
                </div>
              </div>

              {error ? (
                <div className="flex items-start gap-2 text-red-300 bg-red-500/10 border border-red-500/20 rounded-lg p-3">
                  <AlertCircle className="h-5 w-5 mt-0.5" />
                  <div className="text-sm">{error}</div>
                </div>
              ) : null}

              {copied ? (
                <div className="text-green-300 bg-green-500/10 border border-green-500/20 rounded-lg p-3 text-sm">
                  {tEn('auth.activateDiscord.copiedText')}
                </div>
              ) : null}

              {linkData ? (
                <div className="bg-white/5 border border-white/10 rounded-lg p-4">
                  <div className="text-xs text-white/60">{tEn('auth.activateDiscord.commandLabel')}</div>
                  <div className="mt-2 flex items-center justify-between gap-3">
                    <code className="text-white text-sm break-all">{linkData.command}</code>
                    <button
                      type="button"
                      onClick={handleCopy}
                      className="shrink-0 inline-flex items-center gap-2 px-3 py-2 rounded-md bg-white/10 hover:bg-white/15 text-white text-sm"
                    >
                      <Copy className="h-4 w-4" />
                      {tEn('common.copy')}
                    </button>
                  </div>
                  <div className="mt-3 text-xs text-white/60">
                    {tEn('auth.activateDiscord.expiresIn', { minutes: linkData.expires_in_minutes })}
                  </div>
                </div>
              ) : null}

              <div className="flex flex-col gap-3">
                <button
                  type="button"
                  onClick={handleGenerateCode}
                  disabled={isGenerating || isPolling}
                  className="w-full inline-flex items-center justify-center gap-2 px-4 py-3 rounded-lg bg-scum-orange hover:bg-scum-orange/90 disabled:opacity-60 text-white font-semibold"
                >
                  {isGenerating ? <Loader2 className="h-5 w-5 animate-spin" /> : <CheckCircle2 className="h-5 w-5" />}
                  {isPolling ? tEn('auth.activateDiscord.waiting') : tEn('auth.activateDiscord.generate')}
                </button>

                <button
                  type="button"
                  onClick={() => authService.logout().then(() => navigate('/login'))}
                  className="w-full px-4 py-3 rounded-lg bg-white/10 hover:bg-white/15 text-white"
                >
                  {tEn('auth.logout.button')}
                </button>
              </div>
            </div>
          )}
        </div>
      </motion.div>
    </div>
  );
}
