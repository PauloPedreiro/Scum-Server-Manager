import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { ModuleToolPage } from '@/components/tools/ModuleToolPage';
import Swal from 'sweetalert2';
import {
  getShopAdminKits,
  saveShopAdminKit,
  deleteShopAdminKit,
  scanChestToKit,
  type ShopAdminKit,
  type ShopAdminKitItemDetail,
} from '@/services/shopAdmin';
import { Plus, Trash2, Edit2, Package, Sparkles, RefreshCw, X, AlertTriangle, Layers, ChevronDown, ChevronRight } from 'lucide-react';

export default function Kits({ isTab = false }: { isTab?: boolean } = {}) {
  const { t } = useTranslation();
  const [kits, setKits] = useState<ShopAdminKit[]>([]);
  const [loading, setLoading] = useState(false);
  const [expandedKits, setExpandedKits] = useState<Record<string, boolean>>({});

  const toggleKitExpand = (kitId: string) => {
    setExpandedKits(prev => ({
      ...prev,
      [kitId]: !prev[kitId]
    }));
  };

  // Modais de Criação/Edição Manual
  const [manualModalOpen, setManualModalOpen] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [kitId, setKitId] = useState('');
  const [code, setCode] = useState<number | ''>('');
  const [name, setName] = useState('');
  const [price, setPrice] = useState<number | ''>('');
  const [enabled, setEnabled] = useState(true);
  const [onlyOnce, setOnlyOnce] = useState(false);
  const [autoDeliver, setAutoDeliver] = useState(false);
  const [items, setItems] = useState<ShopAdminKitItemDetail[]>([{ setup: '', qty: 1 }]);

  // Modal de Escaneamento de Baú
  const [scanModalOpen, setScanModalOpen] = useState(false);
  const [chestId, setChestId] = useState<number | ''>('');
  const [scanKitId, setScanKitId] = useState('');
  const [scanName, setScanName] = useState('');
  const [scanPrice, setScanPrice] = useState<number | ''>('');
  const [scanEnabled, setScanEnabled] = useState(true);
  const [scanOnlyOnce, setScanOnlyOnce] = useState(false);
  const [scanAutoDeliver, setScanAutoDeliver] = useState(false);
  const [scanCode, setScanCode] = useState<number | ''>('');

  const loadKits = async () => {
    setLoading(true);
    try {
      const res = await getShopAdminKits();
      if (res.success && Array.isArray(res.data)) {
        setKits(res.data);
      } else {
        setKits([]);
      }
    } catch (e) {
      console.error(e);
      setKits([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadKits();
  }, []);

  // Abre modal manual para criação
  const handleOpenCreateManual = () => {
    setIsEditing(false);
    const maxCode = kits.reduce((max, kit) => Math.max(max, kit.code || 0), 0);
    const nextCode = maxCode + 1;
    setCode(nextCode);
    setKitId(String(nextCode));
    setName('');
    setPrice('');
    setEnabled(true);
    setOnlyOnce(false);
    setAutoDeliver(false);
    setItems([{ setup: '', qty: 1 }]);
    setManualModalOpen(true);
  };

  // Abre modal de escaneamento de baú
  const handleOpenScanModal = () => {
    const maxCode = kits.reduce((max, kit) => Math.max(max, kit.code || 0), 0);
    const nextCode = maxCode + 1;
    setScanCode(nextCode);
    setScanKitId(String(nextCode));
    setScanName('');
    setScanPrice('');
    setScanEnabled(true);
    setScanOnlyOnce(false);
    setScanAutoDeliver(false);
    setChestId('');
    setScanModalOpen(true);
  };

  // Abre modal manual para edição
  const handleOpenEditManual = (kit: ShopAdminKit) => {
    setIsEditing(true);
    setKitId(kit.kit_id);
    setCode(kit.code);
    setName(kit.name);
    setPrice(kit.price);
    setEnabled(!!kit.enabled);
    setOnlyOnce(!!kit.only_once);
    setAutoDeliver(!!kit.auto_deliver_on_register);
    setItems(kit.items.length > 0 ? kit.items.map(it => ({ ...it })) : [{ setup: '', qty: 1 }]);
    setManualModalOpen(true);
  };

  // Adiciona linha de item no formulário manual
  const handleAddItemRow = () => {
    setItems([...items, { setup: '', qty: 1 }]);
  };

  // Remove linha de item no formulário manual
  const handleRemoveItemRow = (index: number) => {
    const next = [...items];
    next.splice(index, 1);
    setItems(next.length === 0 ? [{ setup: '', qty: 1 }] : next);
  };

  // Altera campo do item no formulário manual
  const handleItemChange = (index: number, field: keyof ShopAdminKitItemDetail, value: any) => {
    const next = [...items];
    next[index] = { ...next[index], [field]: value };
    setItems(next);
  };

  // Envia formulário manual
  const handleSaveManual = async (e: React.FormEvent) => {
    e.preventDefault();
    const cleanKitId = kitId.trim();
    const cleanName = name.trim();
    if (!cleanKitId) {
      await Swal.fire('Erro', 'Por favor, insira o ID do Kit.', 'error');
      return;
    }
    if (code === '') {
      await Swal.fire('Erro', 'Por favor, insira o Código do Catálogo.', 'error');
      return;
    }
    if (!cleanName) {
      await Swal.fire('Erro', 'Por favor, insira o Nome do Kit.', 'error');
      return;
    }
    if (price === '') {
      await Swal.fire('Erro', 'Por favor, insira o Preço.', 'error');
      return;
    }

    // Filtrar itens vazios
    const validItems = items.filter(it => it.setup.trim() !== '');
    if (validItems.length === 0) {
      await Swal.fire('Erro', 'O Kit precisa conter pelo menos um item válido com setup.', 'error');
      return;
    }

    try {
      const res = await saveShopAdminKit({
        kit_id: cleanKitId,
        code: Number(code),
        name: cleanName,
        price: Number(price),
        enabled: enabled,
        only_once: onlyOnce,
        auto_deliver_on_register: autoDeliver,
        items: validItems.map(it => ({ setup: it.setup.trim(), qty: Number(it.qty) })),
      });

      if (res.success) {
        setManualModalOpen(false);
        await loadKits();
        await Swal.fire({
          icon: 'success',
          title: 'Sucesso',
          text: res.message || `Kit '${cleanName}' salvo com sucesso!`,
          confirmButtonColor: '#f97316',
        });
      } else {
        await Swal.fire('Erro', res.error || 'Falha ao salvar o kit.', 'error');
      }
    } catch (err: any) {
      const msg = err?.response?.data?.error || err?.message || 'Falha ao salvar o kit.';
      await Swal.fire('Erro', msg, 'error');
    }
  };

  // Deleta um Kit
  const handleDeleteKit = async (kit: ShopAdminKit) => {
    const result = await Swal.fire({
      title: 'Tem certeza?',
      text: `Deseja realmente excluir o Kit '${kit.name}'? Esta ação é irreversível.`,
      icon: 'warning',
      showCancelButton: true,
      confirmButtonColor: '#ef4444',
      cancelButtonColor: '#374151',
      confirmButtonText: 'Sim, excluir!',
      cancelButtonText: 'Cancelar',
    });

    if (result.isConfirmed) {
      try {
        const res = await deleteShopAdminKit(kit.kit_id);
        if (res.success) {
          await Swal.fire({
            icon: 'success',
            title: 'Excluído!',
            text: res.message || 'Kit excluído com sucesso.',
            confirmButtonColor: '#f97316',
          });
          await loadKits();
        } else {
          await Swal.fire('Erro', res.error || 'Falha ao excluir o kit.', 'error');
        }
      } catch (err: any) {
        const msg = err?.response?.data?.error || err?.message || 'Falha ao excluir o kit.';
        await Swal.fire('Erro', msg, 'error');
      }
    }
  };

  // Envia formulário de escaneamento de baú
  const handleScanChest = async (e: React.FormEvent) => {
    e.preventDefault();
    if (chestId === '') {
      await Swal.fire('Erro', 'Por favor, insira o ID do Baú.', 'error');
      return;
    }
    const cleanScanKitId = scanKitId.trim().replace(/\s+/g, '_');
    if (!cleanScanKitId) {
      await Swal.fire('Erro', 'Por favor, insira o Código do Kit.', 'error');
      return;
    }
    const cleanScanName = scanName.trim();
    if (!cleanScanName) {
      await Swal.fire('Erro', 'Por favor, insira o Nome do Kit.', 'error');
      return;
    }
    if (scanPrice === '') {
      await Swal.fire('Erro', 'Por favor, insira o Preço.', 'error');
      return;
    }

    try {
      const res = await scanChestToKit({
        chest_id: Number(chestId),
        kit_id: cleanScanKitId,
        name: cleanScanName,
        price: Number(scanPrice),
        enabled: scanEnabled,
        only_once: scanOnlyOnce,
        auto_deliver_on_register: scanAutoDeliver,
        code: scanCode !== '' ? Number(scanCode) : undefined,
      });

      if (res.success) {
        setScanModalOpen(false);
        // Limpar campos de scan
        setChestId('');
        setScanKitId('');
        setScanName('');
        setScanPrice('');
        setScanEnabled(true);
        setScanOnlyOnce(false);
        setScanAutoDeliver(false);
        setScanCode('');
        await loadKits();

        await Swal.fire({
          icon: 'success',
          title: 'Kit Criado!',
          text: res.message || 'Baú escaneado e kit criado com sucesso.',
          confirmButtonColor: '#f97316',
        });
      } else {
        await Swal.fire('Erro', res.error || 'Falha ao escanear o baú.', 'error');
      }
    } catch (err: any) {
      const msg = err?.response?.data?.error || err?.message || 'Falha ao escanear o baú.';
      await Swal.fire('Erro', msg, 'error');
    }
  };

  const renderContent = (
    <>
      <div className="space-y-4">
        {/* Barra de Ações Superior */}
        <div className="card p-4 flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <Layers className="text-scum-orange w-5 h-5" />
            <span className="text-sm font-semibold text-white/95">
              {t('tools.kits.totalKits')}: <span className="text-scum-orange">{kits.length}</span>
            </span>
          </div>

          <div className="flex flex-wrap items-center gap-2 w-full sm:w-auto justify-end">
            <button
              onClick={() => void loadKits()}
              disabled={loading}
              className="p-2 rounded-lg border border-white/15 bg-white/8 text-white/90 shadow-sm hover:text-white hover:bg-white/12 hover:border-white/25 focus:outline-none focus:ring-2 focus:ring-scum-orange/70 disabled:opacity-70 disabled:cursor-not-allowed"
              title="Atualizar lista"
            >
              <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
            </button>

            <button
              onClick={handleOpenScanModal}
              className="flex items-center gap-1.5 px-3 py-2 rounded-lg border border-scum-orange/60 bg-scum-orange/10 text-sm font-semibold text-scum-orange shadow-sm hover:bg-scum-orange/20 hover:border-scum-orange/80 focus:outline-none focus:ring-2 focus:ring-scum-orange/70"
            >
              <Sparkles size={16} />
              {t('tools.kits.scanChest')}
            </button>

            <button
              onClick={handleOpenCreateManual}
              className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-scum-orange text-sm font-semibold text-white shadow-sm hover:bg-scum-orange-hover focus:outline-none focus:ring-2 focus:ring-scum-orange/70"
            >
              <Plus size={16} />
              {t('tools.kits.createManual')}
            </button>
          </div>
        </div>

        {/* Tabela de Kits */}
        <div className="card p-4 overflow-hidden">
          {loading && kits.length === 0 ? (
            <div className="p-8 text-center text-sm text-white/60">
              <RefreshCw className="animate-spin w-8 h-8 mx-auto mb-2 text-scum-orange" />
              Carregando kits...
            </div>
          ) : kits.length === 0 ? (
            <div className="p-8 text-center text-sm text-white/60 space-y-1">
              <Package className="w-12 h-12 mx-auto text-white/25 mb-1" />
              <div className="font-semibold">Nenhum kit cadastrado</div>
              <div className="text-xs">Use os botões acima para cadastrar kits manualmente ou via baú.</div>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-white/10 text-xs font-semibold text-white/60 uppercase">
                    <th className="py-3 px-4 w-10"></th>
                    <th className="py-3 px-4">{t('tools.kits.table.kit')}</th>
                    <th className="py-3 px-4">{t('tools.kits.table.name')}</th>
                    <th className="py-3 px-4 text-right">Preço</th>
                    <th className="py-3 px-4 text-center">Status</th>
                    <th className="py-3 px-4 text-center">{t('tools.kits.table.onlyOnce')}</th>
                    <th className="py-3 px-4">{t('tools.kits.table.items')}</th>
                    <th className="py-3 px-4 text-right">{t('tools.kits.table.actions')}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5 text-sm">
                  {kits.flatMap(kit => {
                    const isExpanded = !!expandedKits[kit.kit_id];
                    return [
                      <tr key={kit.kit_id} className="hover:bg-white/[0.02] transition-colors">
                        <td className="py-3 px-4 text-center">
                          <button
                            onClick={() => toggleKitExpand(kit.kit_id)}
                            className="text-white/40 hover:text-white transition-colors p-1"
                          >
                            {isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                          </button>
                        </td>
                        <td className="py-3 px-4">
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded bg-scum-orange/15 border border-scum-orange/30 text-xs font-bold text-scum-orange font-mono shadow-sm">
                            Kit {kit.code}
                          </span>
                        </td>
                        <td className="py-3 px-4 font-semibold text-white/95">
                          <span>{kit.name}</span>
                          {!!kit.auto_deliver_on_register && (
                            <span className="inline-flex items-center px-2 py-0.5 rounded-full bg-green-500/15 border border-green-500/40 text-xs font-semibold text-green-300 ml-2">
                              Welcome Pack
                            </span>
                          )}
                        </td>
                        <td className="py-3 px-4 text-right tabular-nums text-sm text-white/80">
                          {kit.price.toLocaleString('pt-BR')} coins
                        </td>
                        <td className="py-3 px-4 text-center">
                          {kit.enabled ? (
                            <span className="inline-flex items-center px-2 py-0.5 rounded-full bg-green-500/10 border border-green-500/30 text-xs font-semibold text-green-400">
                              Ativo
                            </span>
                          ) : (
                            <span className="inline-flex items-center px-2 py-0.5 rounded-full bg-white/5 border border-white/10 text-xs font-medium text-white/40">
                              Inativo
                            </span>
                          )}
                        </td>
                        <td className="py-3 px-4 text-center">
                          {kit.only_once ? (
                            <span className="inline-flex items-center px-2 py-0.5 rounded-full bg-amber-500/10 border border-amber-500/30 text-xs font-semibold text-amber-300">
                              {t('tools.kits.table.yes')}
                            </span>
                          ) : (
                            <span className="inline-flex items-center px-2 py-0.5 rounded-full bg-white/5 border border-white/10 text-xs font-medium text-white/55">
                              {t('tools.kits.table.no')}
                            </span>
                          )}
                        </td>
                        <td className="py-3 px-4">
                          <button
                            onClick={() => toggleKitExpand(kit.kit_id)}
                            className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-white/5 border border-white/10 text-xs font-semibold text-white/70 hover:bg-white/10 hover:text-white transition-colors"
                          >
                            <Package size={12} className="text-scum-orange" />
                            <span>{kit.items.length} {t(kit.items.length === 1 ? 'tools.kits.table.itemUnit' : 'tools.kits.table.itemsUnit')}</span>
                            {isExpanded ? <ChevronDown size={12} className="opacity-50" /> : <ChevronRight size={12} className="opacity-50" />}
                          </button>
                        </td>
                        <td className="py-3 px-4 text-right">
                          <div className="inline-flex items-center gap-2">
                            <button
                              onClick={() => handleOpenEditManual(kit)}
                              className="p-1.5 rounded bg-white/5 border border-white/10 text-white/70 hover:text-white hover:bg-white/10 transition-colors"
                              title="Editar Kit"
                            >
                              <Edit2 size={14} />
                            </button>
                            <button
                              onClick={() => void handleDeleteKit(kit)}
                              className="p-1.5 rounded bg-red-500/10 border border-red-500/20 text-red-400 hover:text-red-300 hover:bg-red-500/20 transition-colors"
                              title="Excluir Kit"
                            >
                              <Trash2 size={14} />
                            </button>
                          </div>
                        </td>
                      </tr>,
                      isExpanded && (
                        <tr key={kit.kit_id + '-details'} className="bg-white/[0.01]">
                          <td colSpan={8} className="px-6 py-4 border-t border-b border-white/5 bg-black/10">
                            <div className="space-y-2">
                              <div className="text-xs font-semibold text-white/40 uppercase tracking-wider">Itens Inclusos no Kit</div>
                              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2">
                                {kit.items.length === 0 ? (
                                  <div className="col-span-full text-xs text-white/40 italic">Nenhum item cadastrado neste kit.</div>
                                ) : (
                                  kit.items.map((it, idx) => (
                                    <div
                                      key={idx}
                                      className="flex items-center gap-2.5 px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-xs text-white/80 hover:bg-white/8 hover:border-white/20 transition-colors"
                                    >
                                      <span className="text-scum-orange font-bold font-mono text-sm bg-scum-orange/10 px-2 py-0.5 rounded border border-scum-orange/20">
                                        {it.qty}x
                                      </span>
                                      <span className="font-mono truncate select-all" title={it.setup}>
                                        {it.setup}
                                      </span>
                                    </div>
                                  ))
                                )}
                              </div>
                            </div>
                          </td>
                        </tr>
                      )
                    ];
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* Modal Manual de Cadastro/Edição */}
      {manualModalOpen && (
        <div className="fixed inset-0 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-[#0b1220] border border-white/10 w-full max-w-xl rounded-xl shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between px-6 py-4 border-b border-white/10 bg-white/[0.02]">
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <Layers className="text-scum-orange w-5 h-5" />
                <span>{isEditing ? 'Editar Kit' : 'Criar Kit Manualmente'}</span>
                <span className="ml-1.5 text-xs bg-scum-orange/20 text-scum-orange border border-scum-orange/30 px-2 py-0.5 rounded font-mono font-bold">
                  Código #{code}
                </span>
              </h3>
              <button
                onClick={() => setManualModalOpen(false)}
                className="text-white/60 hover:text-white transition-colors"
              >
                <X size={20} />
              </button>
            </div>

            <form onSubmit={handleSaveManual} className="p-6 space-y-4 max-h-[80vh] overflow-y-auto">
              <input type="hidden" name="code" value={code} />

              <div>
                <label className="block text-xs font-semibold uppercase text-white/60 mb-1.5">Nome do Kit</label>
                <input
                  type="text"
                  required
                  placeholder="Ex: Kit Inicial Sobrevivente"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-white text-sm focus:outline-none focus:ring-2 focus:ring-scum-orange"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase text-white/60 mb-1.5">Preço (Coins)</label>
                <input
                  type="number"
                  required
                  min={0}
                  placeholder="Ex: 500"
                  value={price}
                  onChange={(e) => setPrice(e.target.value === '' ? '' : Number(e.target.value))}
                  className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-white text-sm focus:outline-none focus:ring-2 focus:ring-scum-orange"
                />
              </div>

              <div className="flex items-center gap-3">
                <input
                  type="checkbox"
                  id="enabled"
                  checked={enabled}
                  onChange={(e) => setEnabled(e.target.checked)}
                  className="w-4 h-4 text-scum-orange border-white/20 bg-white/5 rounded focus:ring-scum-orange"
                />
                <label htmlFor="enabled" className="text-xs text-white/80 cursor-pointer select-none">
                  Ativar imediatamente no catálogo da loja
                </label>
              </div>

              {/* Checkbox Compra Única */}
              <div className={`flex items-center gap-3 p-3 rounded-lg border ${autoDeliver ? 'border-white/10 bg-white/5 opacity-50' : 'border-amber-500/20 bg-amber-500/5'}`}>
                <input
                  type="checkbox"
                  id="onlyOnce"
                  checked={autoDeliver ? true : onlyOnce}
                  onChange={(e) => setOnlyOnce(e.target.checked)}
                  disabled={autoDeliver}
                  className="w-4 h-4 text-scum-orange border-white/20 bg-white/5 rounded focus:ring-scum-orange disabled:cursor-not-allowed"
                />
                <label htmlFor="onlyOnce" className="text-sm text-white/80 cursor-pointer select-none">
                  <span className="font-semibold text-white block">Permitir compra apenas uma vez</span>
                  <span className="text-xs text-white/50 block mt-0.5">Indicado para Welcome Kits. Evita recompra.</span>
                </label>
              </div>

              {/* Checkbox Entrega Automática no Registro */}
              <div className="flex items-center gap-3 p-3 rounded-lg border border-green-500/20 bg-green-500/5">
                <input
                  type="checkbox"
                  id="autoDeliver"
                  checked={autoDeliver}
                  onChange={(e) => setAutoDeliver(e.target.checked)}
                  className="w-4 h-4 text-scum-orange border-white/20 bg-white/5 rounded focus:ring-scum-orange"
                />
                <label htmlFor="autoDeliver" className="text-sm text-white/80 cursor-pointer select-none">
                  <span className="font-semibold text-white block">Entregar automaticamente no registro</span>
                  <span className="text-xs text-white/50 block mt-0.5">
                    Entrega este kit ao jogador no momento do registro via Discord. Só 1 kit pode ter esta opção ativa.
                  </span>
                </label>
              </div>

              {/* Seção de Itens Dinâmicos */}
              <div className="space-y-2.5 pt-2">
                <div className="flex items-center justify-between border-b border-white/10 pb-1.5">
                  <span className="text-xs font-bold uppercase text-white/85">Itens do Kit</span>
                  <button
                    type="button"
                    onClick={handleAddItemRow}
                    className="text-xs font-semibold text-scum-orange hover:text-scum-orange-hover"
                  >
                    + Adicionar Item
                  </button>
                </div>

                <div className="space-y-2 max-h-[200px] overflow-y-auto pr-1">
                  {items.map((it, idx) => (
                    <div key={idx} className="flex gap-2 items-center">
                      <div className="flex-1">
                        <input
                          type="text"
                          required
                          placeholder="Classe in-game (ex: Weapon_MP5)"
                          value={it.setup}
                          onChange={(e) => handleItemChange(idx, 'setup', e.target.value)}
                          className="w-full px-3 py-1.5 rounded-lg bg-white/5 border border-white/10 text-white text-xs focus:outline-none focus:ring-2 focus:ring-scum-orange font-mono"
                        />
                      </div>
                      <div className="w-20">
                        <input
                          type="number"
                          required
                          min={1}
                          placeholder="Qtd"
                          value={it.qty}
                          onChange={(e) => handleItemChange(idx, 'qty', e.target.value === '' ? '' : Number(e.target.value))}
                          className="w-full px-3 py-1.5 rounded-lg bg-white/5 border border-white/10 text-white text-xs text-center focus:outline-none focus:ring-2 focus:ring-scum-orange"
                        />
                      </div>
                      <button
                        type="button"
                        onClick={() => handleRemoveItemRow(idx)}
                        className="p-2 text-white/40 hover:text-red-400 hover:bg-white/5 rounded transition-colors"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  ))}
                </div>
              </div>

              {/* Botões do Modal */}
              <div className="flex items-center justify-end gap-2 border-t border-white/10 pt-4 mt-6">
                <button
                  type="button"
                  onClick={() => setManualModalOpen(false)}
                  className="px-4 py-2 rounded-lg border border-white/15 bg-white/8 text-sm font-medium text-white/95 hover:bg-white/12 transition-colors"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-lg bg-scum-orange text-sm font-semibold text-white hover:bg-scum-orange-hover transition-colors"
                >
                  Salvar Kit
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal de Escaneamento de Baú */}
      {scanModalOpen && (
        <div className="fixed inset-0 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-[#0b1220] border border-white/10 w-full max-w-md rounded-xl shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between px-6 py-4 border-b border-white/10 bg-white/[0.02]">
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <Sparkles className="text-scum-orange w-5 h-5 animate-pulse" />
                <span>Escanear Baú para Novo Kit</span>
                <span className="ml-1.5 text-xs bg-scum-orange/20 text-scum-orange border border-scum-orange/30 px-2 py-0.5 rounded font-mono font-bold">
                  Código #{scanCode}
                </span>
              </h3>
              <button
                onClick={() => setScanModalOpen(false)}
                className="text-white/60 hover:text-white transition-colors"
              >
                <X size={20} />
              </button>
            </div>

            <form onSubmit={handleScanChest} className="p-6 space-y-4">
              <input type="hidden" name="scanCode" value={scanCode} />
              <div>
                <label className="block text-xs font-semibold uppercase text-white/60 mb-1.5">ID do Baú (In-game)</label>
                <input
                  type="number"
                  required
                  placeholder="Ex: 999999"
                  value={chestId}
                  onChange={(e) => setChestId(e.target.value === '' ? '' : Number(e.target.value))}
                  className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-white text-sm focus:outline-none focus:ring-2 focus:ring-scum-orange"
                />
                <p className="text-[10px] text-white/40 mt-1">O ID numérico do baú sincronizado no mapa.</p>
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase text-white/60 mb-1.5">Nome de Exibição</label>
                <input
                  type="text"
                  required
                  placeholder="Ex: Kit Premium Militar"
                  value={scanName}
                  onChange={(e) => setScanName(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-white text-sm focus:outline-none focus:ring-2 focus:ring-scum-orange"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase text-white/60 mb-1.5">Preço (Coins)</label>
                <input
                  type="number"
                  required
                  min={0}
                  placeholder="Ex: 500"
                  value={scanPrice}
                  onChange={(e) => setScanPrice(e.target.value === '' ? '' : Number(e.target.value))}
                  className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-white text-sm focus:outline-none focus:ring-2 focus:ring-scum-orange"
                />
              </div>

              {/* Toggles */}
              <div className="space-y-2 pt-1.5">
                <div className="flex items-center gap-3">
                  <input
                    type="checkbox"
                    id="scanEnabled"
                    checked={scanEnabled}
                    onChange={(e) => setScanEnabled(e.target.checked)}
                    className="w-4 h-4 text-scum-orange border-white/20 bg-white/5 rounded focus:ring-scum-orange"
                  />
                  <label htmlFor="scanEnabled" className="text-xs text-white/80 cursor-pointer select-none">
                    Ativar imediatamente no catálogo da loja
                  </label>
                </div>

                <div className="flex items-center gap-3">
                  <input
                    type="checkbox"
                    id="scanOnlyOnce"
                    checked={scanAutoDeliver ? true : scanOnlyOnce}
                    onChange={(e) => setScanOnlyOnce(e.target.checked)}
                    disabled={scanAutoDeliver}
                    className="w-4 h-4 text-scum-orange border-white/20 bg-white/5 rounded focus:ring-scum-orange disabled:cursor-not-allowed"
                  />
                  <label htmlFor="scanOnlyOnce" className="text-xs text-white/80 cursor-pointer select-none">
                    Compra única? (Impede recompra - ex: Welcome Kit)
                  </label>
                </div>

                <div className="flex items-center gap-3 p-3 rounded-lg border border-green-500/20 bg-green-500/5">
                  <input
                    type="checkbox"
                    id="scanAutoDeliver"
                    checked={scanAutoDeliver}
                    onChange={(e) => setScanAutoDeliver(e.target.checked)}
                    className="w-4 h-4 text-scum-orange border-white/20 bg-white/5 rounded focus:ring-scum-orange"
                  />
                  <label htmlFor="scanAutoDeliver" className="text-sm text-white/80 cursor-pointer select-none">
                    <span className="font-semibold text-white block">Entregar automaticamente no registro</span>
                    <span className="text-xs text-white/50 block mt-0.5">
                      Entrega este kit ao jogador no momento do registro via Discord. Só 1 kit pode ter esta opção ativa.
                    </span>
                  </label>
                </div>
              </div>

              {/* Botões do Modal */}
              <div className="flex items-center justify-end gap-2 border-t border-white/10 pt-4 mt-6">
                <button
                  type="button"
                  onClick={() => setScanModalOpen(false)}
                  className="px-4 py-2 rounded-lg border border-white/15 bg-white/8 text-sm font-medium text-white/95 hover:bg-white/12 transition-colors"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-lg bg-scum-orange text-sm font-semibold text-white hover:bg-scum-orange-hover transition-colors"
                >
                  Escanear e Criar
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );

  if (isTab) {
    return renderContent;
  }

  return (
    <ModuleToolPage
      title={t('tools.kits.title')}
      subtitle={t('tools.kits.subtitle')}
    >
      {renderContent}
    </ModuleToolPage>
  );
}
