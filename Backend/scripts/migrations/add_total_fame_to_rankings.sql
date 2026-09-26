-- ==========================================
-- Migração: Adicionar coluna total_fame na tabela rankings
-- Data: 2025-12-02
-- Descrição: Adiciona a coluna total_fame da tabela player_fame_totals na tabela rankings
-- ==========================================

-- Adicionar coluna total_fame
ALTER TABLE rankings ADD COLUMN total_fame REAL DEFAULT 0.0;

-- Criar índice para ordenação rápida
CREATE INDEX IF NOT EXISTS idx_rankings_total_fame ON rankings(total_fame DESC);

-- Atualizar valores existentes com dados de player_fame_totals (opcional)
-- Isso preenche os valores para jogadores que já têm fama registrada
UPDATE rankings
SET total_fame = (
    SELECT COALESCE(total_fame, 0.0)
    FROM player_fame_totals
    WHERE player_fame_totals.steam_id = rankings.steam_id
)
WHERE EXISTS (
    SELECT 1
    FROM player_fame_totals
    WHERE player_fame_totals.steam_id = rankings.steam_id
);

-- Verificar se a coluna foi adicionada corretamente
-- SELECT sql FROM sqlite_master WHERE type='table' AND name='rankings';

