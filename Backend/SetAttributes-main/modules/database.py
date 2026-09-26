import sqlite3
import struct
from .utils import double_to_hex, get_valid_float

# --- FUNÇÕES PURAS (USADAS PELA GUI E CLI) ---

def fetch_prisoners(cursor):
    """
    Retorna uma lista de dicionários com os prisioneiros encontrados.
    Formato: [{'id': 1, 'steam_id': '765...', 'name': 'Player1'}, ...]
    """
    try:
        query = """
            SELECT p.id, u.user_id, u.name 
            FROM user_profile u
            INNER JOIN prisoner p ON u.prisoner_id = p.id
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        
        results = []
        if rows:
            for row in rows:
                results.append({
                    'id': row[0],
                    'steam_id': str(row[1]) if row[1] else "N/A",
                    'name': row[2] if row[2] else "N/A"
                })
        else:
            # Fallback
            cursor.execute("SELECT id FROM prisoner")
            rows_p = cursor.fetchall()
            for row in rows_p:
                results.append({
                    'id': row[0],
                    'steam_id': "N/A",
                    'name': f"Prisoner {row[0]}"
                })
        return results
    except sqlite3.Error as e:
        print(f"[ERRO SQL] {e}")
        return []

def get_prisoner_attributes(cursor, p_id):
    """
    Lê os atributos atuais do prisioneiro e retorna um dict.
    """
    cursor.execute("SELECT body_simulation FROM prisoner WHERE id = ?", (p_id,))
    row = cursor.fetchone()
    if not row:
        return None
        
    data = bytes(row[0]) # Imutável para leitura
    
    attrs_map = {
        b'BaseStrength': "strength",
        b'BaseConstitution': "constitution", 
        b'BaseDexterity': "dexterity",
        b'BaseIntelligence': "intelligence"
    }
    
    values = {}
    for key, slug in attrs_map.items():
        pos = data.find(key)
        val = 0.0
        if pos != -1:
            prop = data.find(b'DoubleProperty', pos)
            if prop != -1:
                offset = prop + 24
                # unpack retorna tupla
                val = struct.unpack('<d', data[offset:offset+8])[0]
        values[slug] = val
    
    return values

def update_prisoner_attributes(cursor, p_id, new_values_dict):
    """
    Atualiza o BLOB com os novos valores.
    new_values_dict ex: {'strength': 5.0, 'constitution': 3.0 ...}
    Retorna True/False.
    """
    try:
        cursor.execute("SELECT body_simulation FROM prisoner WHERE id = ?", (p_id,))
        row = cursor.fetchone()
        if not row: return False, []
        
        data = bytearray(row[0])
        
        slug_to_bytes = {
            'strength': b'BaseStrength',
            'constitution': b'BaseConstitution',
            'dexterity': b'BaseDexterity',
            'intelligence': b'BaseIntelligence'
        }
        
        changes = 0
        logs = []

        for slug, val in new_values_dict.items():
            key = slug_to_bytes.get(slug)
            if not key: continue
            
            val_bytes = double_to_hex(val)
            pos = data.find(key)
            if pos != -1:
                prop = data.find(b'DoubleProperty', pos)
                if prop != -1:
                    offset = prop + 24
                    if offset + 8 <= len(data):
                        # Ler valor antigo para log
                        old_val = struct.unpack('<d', data[offset:offset+8])[0]
                        
                        if old_val != val:
                            data[offset:offset+8] = val_bytes
                            changes += 1
                            logs.append(f"mudança [{slug}]: {old_val:.2f} -> {val:.2f}")
        
        if changes > 0:
            cursor.execute("UPDATE prisoner SET body_simulation = ? WHERE id = ?", (data, p_id))
            return True, logs
        return False, []
        
    except Exception as e:
        print(f"[ERRO UPDATE] {e}")
        return False, []

# --- FUNÇÕES CLI (LEGADO/TEXTO) ---

def select_prisoner(cursor):
    """Versão CLI que usa input()."""
    prisoners = fetch_prisoners(cursor)
    if not prisoners:
        print("Nenhum prisioneiro encontrado.")
        return None
        
    lookup = {}
    print(f"\n{'ID (DB)':<10} | {'SteamID':<20} | {'Nome':<20}")
    print("-" * 60)
    
    for p in prisoners:
        pid = str(p['id'])
        sid = p['steam_id']
        lookup[pid] = p['id']
        if sid != "N/A":
            lookup[sid] = p['id']
        print(f"{p['id']:<10} | {p['steam_id']:<20} | {p['name']:<20}")
        
    while True:
        sel = input("\nDigite a SteamID (ou ID do banco) para confirmar: ").strip()
        if sel in lookup:
            return lookup[sel]
        print("Não encontrado.")

def process_scum_db(db_path):
    """Versão CLI completa."""
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        p_id = select_prisoner(cursor)
        if p_id is None: return False

        # Leitura
        current = get_prisoner_attributes(cursor, p_id)
        if not current:
            print("Erro ao ler atributos.")
            return False
            
        print("\n--- Valores Atuais ---")
        label_map = {'strength': 'Força', 'constitution': 'Constituição', 'dexterity': 'Destreza', 'intelligence': 'Inteligência'}
        for k, v in current.items():
            print(f"{label_map[k]:<15}: {v:.2f}")

        # Inputs
        print("\n--- Definir Novos Atributos ---")
        new_vals = {}
        new_vals['strength'] = get_valid_float("Nova Força (1.0-8.0): ", 1.0, 8.0)
        new_vals['constitution'] = get_valid_float("Nova Constituição (1.0-5.0): ", 1.0, 5.0)
        new_vals['dexterity'] = get_valid_float("Nova Destreza (1.0-5.0): ", 1.0, 5.0)
        new_vals['intelligence'] = get_valid_float("Nova Inteligência (1.0-5.0): ", 1.0, 5.0)

        # Resumo
        print("\n=== RESUMO ===")
        for k in current.keys():
             print(f"{label_map[k]:<15} | {current[k]:<8.2f} -> {new_vals[k]:<8.2f}")

        if input("\nConfirmar alterações? (S/N): ").lower() != 's':
            return False

        # Update
        success, logs = update_prisoner_attributes(cursor, p_id, new_vals)
        if success:
            conn.commit()
            for l in logs: print(f"[LOG] {l}")
            print("[SUCESSO] Dados gravados.")
            return True
        else:
            print("[ERRO] Falha na gravação.")
            return False

    except Exception as e:
        print(f"[ERRO DB] {e}")
        return False
    finally:
        if conn: conn.close()
