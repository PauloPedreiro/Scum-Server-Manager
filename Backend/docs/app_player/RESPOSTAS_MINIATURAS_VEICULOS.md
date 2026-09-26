# Respostas SSM - Miniaturas de Veiculos (Player App)

Data: 2026-02-19

---

## 1) Qual campo e o "oficial" para o nome de UI do veiculo?

**Usar `vehicle_class_display`.**

| Campo                   | Exemplo                 | Uso                                      |
|-------------------------|-------------------------|------------------------------------------|
| `vehicle_class`         | `BPC_Wolfswagen`        | Valor bruto do SCUM.db (campo `entity.class`). Uso interno/debug. |
| `vehicle_class_display` | `Wolfswagen`            | **Nome de UI.** Gerado pelo SSM removendo prefixos (`BPC_`, `BP_`) e sufixos (`_ES`, `_C`), e substituindo `_` por espaco. |

### Como o SSM gera `vehicle_class_display`

```python
def _format_vehicle_class_display(vehicle_class: str) -> str:
    if not vehicle_class:
        return "Desconhecido"
    return (vehicle_class
        .replace("BPC_", "")
        .replace("BP_", "")
        .replace("_ES", "")
        .replace("_C", "")
        .replace("_", " ")
        .strip())
```

### Recomendacao

- Usar **`vehicle_class_display`** para:
  - Titulo do card
  - Montar caminho da imagem
- Garantia: este campo **sempre vem preenchido** (fallback para `"Desconhecido"` se `vehicle_class` for nulo).
- O valor e **consistente** entre lista (`/api/player/vehicles`), resumo (`/summary`) e detalhe (`/<id>`).

---

## 2) O nome pode conter espacos/caracteres especiais? Capitalizacao e estavel?

### Sim, pode conter espacos.

A funcao substitui `_` por espaco. Exemplos reais:

| `vehicle_class` (SCUM.db)  | `vehicle_class_display` (API) |
|----------------------------|-------------------------------|
| `BPC_Wolfswagen`           | `Wolfswagen`                  |
| `BPC_Dirtbike`             | `Dirtbike`                    |
| `BPC_Rager`                | `Rager`                       |
| `BPC_Laika`                | `Laika`                       |
| `BPC_RIS`                  | `RIS`                         |
| `BPC_Cruiser`              | `Cruiser`                     |
| `BPC_Tractor`              | `Tractor`                     |
| `BPC_SUP`                  | `SUP`                         |
| `BPC_Barba`                | `Barba`                       |
| `BPC_CityBike`             | `CityBike`                    |
| `BPC_MountainBike`         | `MountainBike`                |
| `BPC_BigRaft`              | `BigRaft`                     |
| `BPC_SmallRaft`            | `SmallRaft`                   |
| `BPC_Kinglet_Duster`       | `Kinglet Duster`              |
| `BPC_Kinglet_Mariner`      | `Kinglet Mariner`             |
| `BP_Wheelbarrow_Imp`       | `Wheelbarrow Imp`             |
| `BP_Wheelbarrow_Met`       | `Wheelbarrow Met`             |

### Sobre caracteres especiais

- **Sem acentos**, sem Unicode especial. Nomes vem do SCUM.db em ASCII.
- **Sem barras, pontos, ou caracteres ilegais** em filenames.

### Sobre capitalizacao

- **Deterministica e estavel.** O SSM preserva o case original do SCUM.db (PascalCase).
- `Wolfswagen` sempre sera `Wolfswagen`, nunca `wolfswagen` ou `WOLFSWAGEN`.
- `RIS` sempre sera `RIS` (sigla em maiusculas).
- Novos veiculos adicionados pelo SCUM seguirao o mesmo padrao (PascalCase definido pelos devs do jogo).

---

## 3) Convencao de arquivo recomendada pelo SSM

Dado que `vehicle_class_display` pode conter **espacos** (ex: `Kinglet Duster`), a recomendacao e:

### Opcao recomendada: manter nome literal no filename

```
/static/images/vehicles/Wolfswagen.webp
/static/images/vehicles/Dirtbike.webp
/static/images/vehicles/Kinglet Duster.webp
/static/images/vehicles/RIS.webp
/static/images/vehicles/Wheelbarrow Imp.webp
```

Motivo: evita logica extra de conversao. O frontend monta a URL direto:

```javascript
const imageUrl = `/static/images/vehicles/${vehicle.vehicle_class_display}.webp`;
```

### Se preferirem evitar espacos no filename

Usar replace de espaco por `_` **apenas no frontend** ao montar a URL:

```javascript
const filename = vehicle.vehicle_class_display.replace(/ /g, '_');
const imageUrl = `/static/images/vehicles/${filename}.webp`;
```

E nomear os arquivos assim:

```
/static/images/vehicles/Kinglet_Duster.webp
/static/images/vehicles/Wheelbarrow_Imp.webp
```

Neste caso, **nao precisa de mapa especial** — a regra e universal (espaco -> `_`).

---

## 4) Lista completa de veiculos conhecidos (para criar imagens)

Abaixo, todos os veiculos conhecidos pelo SSM ate esta data:

| `vehicle_class_display`  | Tipo        |
|--------------------------|-------------|
| `Barba`                  | Barco       |
| `BigRaft`                | Barco       |
| `CityBike`               | Bicicleta   |
| `Cruiser`                | Carro       |
| `Dirtbike`               | Moto        |
| `Kinglet Duster`         | Carro       |
| `Kinglet Mariner`        | Carro       |
| `Laika`                  | Carro       |
| `MountainBike`           | Bicicleta   |
| `Rager`                  | Carro       |
| `RIS`                    | Carro       |
| `SmallRaft`              | Barco       |
| `SUP`                    | Barco       |
| `Tractor`                | Veiculo     |
| `Wheelbarrow Imp`        | Carrinho    |
| `Wheelbarrow Met`        | Carrinho    |
| `Wolfswagen`             | Carro       |

> **Nota:** O SCUM pode adicionar novos veiculos em atualizacoes futuras. Quando isso acontece, o SSM descobre automaticamente e o `vehicle_class_display` sera gerado pela mesma regra (remover prefixos, substituir `_` por espaco). O frontend pode tratar imagens ausentes com a estrategia "sem fallback" ja planejada.

---

## 5) Observacao sobre o `vehicle_class_display` vs `get_vehicle_display_name`

O SSM possui internamente **dois metodos** de formatacao:

| Metodo                             | Onde e usado        | Resultado para `BPC_Kinglet_Duster` |
|------------------------------------|---------------------|--------------------------------------|
| `_format_vehicle_class_display()`  | **API player-scoped** (o que o Gestao consome) | `Kinglet Duster` |
| `get_vehicle_display_name()`       | Admin/notificacoes Discord internas           | `Kinglet Duster` (via mapa hardcoded) |

**Para o Player App, o campo `vehicle_class_display` da API e a unica fonte de verdade.** O Gestao nao precisa se preocupar com o metodo interno do admin.

---

## Resumo de decisoes

| Decisao                        | Valor                                         |
|-------------------------------|-----------------------------------------------|
| Campo canonico para nome       | `vehicle_class_display`                       |
| Pode conter espacos?           | Sim (ex: `Kinglet Duster`)                    |
| Caracteres especiais?          | Nao (somente ASCII, sem acentos)              |
| Case estavel?                  | Sim (PascalCase, determinístico)              |
| Formato de imagem              | `.webp`                                       |
| Tamanho miniatura              | 64x64 ou 72x72                                |
| Fallback visual                | Nenhum (`<img>` oculto em `error`)            |
| Convencao filename             | A cargo do Gestao (literal ou espaco->`_`)    |
