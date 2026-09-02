# Leite Estética Automotiva

Especificação funcional e catálogo de serviços para o site com agendamento.
Fonte dos preços: tabela manuscrita da loja (foto de 17/02/2022). Revalidar valores com o Leite antes de publicar.

Local: Duartina, interior de São Paulo.
Serviços: lavagem, detalhamento e higienização interna de carros, SUVs e caminhonetes.

---

## 1. Tabela de preços

Valores base referentes a **carro de passeio**.

| Código | Serviço | Valor base | Duração estimada |
|---|---|---|---|
| `simples` | Lavagem simples | R$ 80,00 | 1 hora |
| `detalhamento` | Lavagem com detalhamento | R$ 150,00 | 3 horas |
| `completo` | Detalhamento completo com higienização | R$ 600,00 | dia inteiro |

> Duração é estimativa minha para montar a grade de horários. Confirmar com a loja.

### 1.1 Lavagem simples (R$ 80,00)

- Limpeza interna sem detalhamento
- Lavagem externa
- Limpeza da caixa de rodas

### 1.2 Lavagem com detalhamento (R$ 150,00)

- Limpeza interna com detalhamento
- Lavagem externa com detalhamento e cera
- Limpeza da caixa de rodas
- Selante nos pneus

### 1.3 Detalhamento completo com higienização (R$ 600,00)

- Higienização interna com detalhamento
- Limpeza de bancos, carpete, teto e lateral das portas
- Lavagem externa com detalhamento, descontaminação da pintura e cera
- Revitalização das partes plásticas externas
- Limpeza da caixa de rodas
- Selante nos pneus
- Remoção de chuva ácida dos vidros

### 1.4 Acréscimo por porte do veículo

A tabela original diz apenas "SUV: valor tem acréscimo" e "Caminhonete: valor tem acréscimo", sem número.
Os valores abaixo são **placeholders** usados no protótipo. Substituir pelos reais.

| Código | Porte | Acréscimo (placeholder) |
|---|---|---|
| `carro` | Carro | R$ 0,00 |
| `suv` | SUV | R$ 30,00 |
| `caminhonete` | Caminhonete | R$ 50,00 |

Regra de cálculo:

```
valorFinal = servico.precoBase + porte.acrescimo
```

Decisão de produto em aberto: o acréscimo é valor fixo ou percentual sobre o serviço? Se for percentual, trocar a fórmula para `precoBase * (1 + porte.percentual)`.

---

## 2. Catálogo em código

### 2.1 JSON

```json
{
  "servicos": [
    {
      "codigo": "simples",
      "nome": "Lavagem simples",
      "precoBase": 80.00,
      "duracaoMinutos": 60,
      "itens": [
        "Limpeza interna sem detalhamento",
        "Lavagem externa",
        "Limpeza da caixa de rodas"
      ]
    },
    {
      "codigo": "detalhamento",
      "nome": "Lavagem com detalhamento",
      "precoBase": 150.00,
      "duracaoMinutos": 180,
      "itens": [
        "Limpeza interna com detalhamento",
        "Lavagem externa com detalhamento e cera",
        "Limpeza da caixa de rodas",
        "Selante nos pneus"
      ]
    },
    {
      "codigo": "completo",
      "nome": "Detalhamento completo com higienização",
      "precoBase": 600.00,
      "duracaoMinutos": 480,
      "itens": [
        "Higienização interna com detalhamento",
        "Limpeza de bancos, carpete, teto e lateral das portas",
        "Lavagem externa com detalhamento, descontaminação da pintura e cera",
        "Revitalização das partes plásticas externas",
        "Limpeza da caixa de rodas",
        "Selante nos pneus",
        "Remoção de chuva ácida dos vidros"
      ]
    }
  ],
  "portes": [
    { "codigo": "carro",       "nome": "Carro",       "acrescimo": 0.00 },
    { "codigo": "suv",         "nome": "SUV",         "acrescimo": 30.00 },
    { "codigo": "caminhonete", "nome": "Caminhonete", "acrescimo": 50.00 }
  ]
}
```

### 2.2 TypeScript

```ts
export type CodigoServico = "simples" | "detalhamento" | "completo";
export type CodigoPorte = "carro" | "suv" | "caminhonete";

export interface Servico {
  codigo: CodigoServico;
  nome: string;
  precoBase: number;      // em reais
  duracaoMinutos: number;
  itens: string[];
}

export interface Porte {
  codigo: CodigoPorte;
  nome: string;
  acrescimo: number;      // em reais
}

export const SERVICOS: Record<CodigoServico, Servico> = {
  simples: {
    codigo: "simples",
    nome: "Lavagem simples",
    precoBase: 80,
    duracaoMinutos: 60,
    itens: [
      "Limpeza interna sem detalhamento",
      "Lavagem externa",
      "Limpeza da caixa de rodas",
    ],
  },
  detalhamento: {
    codigo: "detalhamento",
    nome: "Lavagem com detalhamento",
    precoBase: 150,
    duracaoMinutos: 180,
    itens: [
      "Limpeza interna com detalhamento",
      "Lavagem externa com detalhamento e cera",
      "Limpeza da caixa de rodas",
      "Selante nos pneus",
    ],
  },
  completo: {
    codigo: "completo",
    nome: "Detalhamento completo com higienização",
    precoBase: 600,
    duracaoMinutos: 480,
    itens: [
      "Higienização interna com detalhamento",
      "Limpeza de bancos, carpete, teto e lateral das portas",
      "Lavagem externa com detalhamento, descontaminação da pintura e cera",
      "Revitalização das partes plásticas externas",
      "Limpeza da caixa de rodas",
      "Selante nos pneus",
      "Remoção de chuva ácida dos vidros",
    ],
  },
};

export const PORTES: Record<CodigoPorte, Porte> = {
  carro:       { codigo: "carro",       nome: "Carro",       acrescimo: 0 },
  suv:         { codigo: "suv",         nome: "SUV",         acrescimo: 30 },
  caminhonete: { codigo: "caminhonete", nome: "Caminhonete", acrescimo: 50 },
};

export function calcularValor(servico: CodigoServico, porte: CodigoPorte): number {
  return SERVICOS[servico].precoBase + PORTES[porte].acrescimo;
}
```

---

## 3. Agendamento

### 3.1 Campos do formulário

| Campo | Tipo | Obrigatório | Validação |
|---|---|---|---|
| `nome` | texto | sim | mínimo 2 caracteres |
| `telefone` | texto | sim | 10 ou 11 dígitos após remover a máscara |
| `veiculo` | texto | não | modelo e cor, texto livre |
| `porte` | enum | sim | `carro`, `suv`, `caminhonete` |
| `servico` | enum | sim | `simples`, `detalhamento`, `completo` |
| `data` | date | sim | não pode ser anterior a hoje |
| `hora` | enum | sim | precisa estar livre na data escolhida |

### 3.2 Grade de horários

Grade fixa de 1 em 1 hora, sem o horário de almoço:

```
08:00  09:00  10:00  11:00  13:00  14:00  15:00  16:00  17:00
```

Regras aplicadas no protótipo:

- Horário já ocupado na data escolhida aparece riscado e não pode ser selecionado.
- A checagem de disponibilidade é por par `data` mais `hora`.
- Só um veículo por slot.

Melhorias que ficam para a versão real:

- Bloquear slots conforme a duração do serviço. O detalhamento completo ocupa o dia todo, então não deveria sobrar horário livre naquele dia.
- Considerar quantas vagas ou boxes a loja atende em paralelo.
- Fechar domingo e limitar sábado até as 13h.
- Bloquear feriados e datas de folga pelo painel do dono.

### 3.3 Estados do agendamento

`pendente` na criação, `confirmado` após o Leite responder no WhatsApp, `concluido` após a entrega, `cancelado` quando o cliente desiste.

---

## 4. Modelo de dados

```sql
CREATE TABLE porte (
    codigo      VARCHAR(20)  NOT NULL PRIMARY KEY,
    nome        VARCHAR(40)  NOT NULL,
    acrescimo   DECIMAL(10,2) NOT NULL DEFAULT 0
);

CREATE TABLE servico (
    codigo            VARCHAR(20)  NOT NULL PRIMARY KEY,
    nome              VARCHAR(80)  NOT NULL,
    preco_base        DECIMAL(10,2) NOT NULL,
    duracao_minutos   INT          NOT NULL,
    ativo             BIT          NOT NULL DEFAULT 1
);

CREATE TABLE servico_item (
    id            INT IDENTITY(1,1) PRIMARY KEY,
    servico_cod   VARCHAR(20)  NOT NULL REFERENCES servico(codigo),
    ordem         INT          NOT NULL,
    descricao     VARCHAR(200) NOT NULL
);

CREATE TABLE agendamento (
    id            INT IDENTITY(1,1) PRIMARY KEY,
    nome          VARCHAR(120) NOT NULL,
    telefone      VARCHAR(20)  NOT NULL,
    veiculo       VARCHAR(120) NULL,
    porte_cod     VARCHAR(20)  NOT NULL REFERENCES porte(codigo),
    servico_cod   VARCHAR(20)  NOT NULL REFERENCES servico(codigo),
    data          DATE         NOT NULL,
    hora          TIME(0)      NOT NULL,
    valor         DECIMAL(10,2) NOT NULL,
    situacao      VARCHAR(20)  NOT NULL DEFAULT 'pendente',
    criado_em     DATETIME2(0) NOT NULL DEFAULT SYSDATETIME(),
    CONSTRAINT uq_agendamento_slot UNIQUE (data, hora)
);

CREATE INDEX ix_agendamento_data ON agendamento (data) INCLUDE (hora, situacao);
```

A constraint `uq_agendamento_slot` é o que garante, no banco, que dois clientes não peguem o mesmo horário em uma corrida de requisições. A validação na tela é conveniência, a do banco é a que vale. Se a loja passar a atender mais de um carro por vez, trocar por uma coluna `box` e mudar a unique para `(data, hora, box)`.

O `valor` fica gravado no agendamento de propósito. Se o preço da tabela mudar depois, o histórico continua correto.

---

## 5. Endpoints sugeridos

| Método | Rota | Descrição |
|---|---|---|
| GET | `/api/servicos` | catálogo com itens e preços |
| GET | `/api/disponibilidade?data=YYYY-MM-DD` | horários livres e ocupados do dia |
| POST | `/api/agendamentos` | cria o agendamento e devolve o valor calculado |
| GET | `/api/agendamentos?data=YYYY-MM-DD` | agenda do dia, uso interno |
| PATCH | `/api/agendamentos/{id}` | muda a situação |

O valor nunca deve vir do front. O cliente envia `servico` e `porte`, e o backend calcula o preço com a tabela oficial.

---

## 6. Pendências a confirmar com o Leite

1. Valor real do acréscimo de SUV e de caminhonete, fixo ou percentual.
2. Duração real de cada serviço e quantos carros ele atende ao mesmo tempo.
3. Horário de funcionamento e dias de folga.
4. Telefone, e-mail e endereço para o rodapé.
5. Formas de pagamento e se cobra sinal no agendamento do serviço de R$ 600,00.
6. Se quer receber os agendamentos por WhatsApp, e-mail ou por um painel próprio.
