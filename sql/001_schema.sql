-- Leite Estetica Automotiva :: schema
-- Secao 5 da ARQUITETURA + secao 4 da especificacao do catalogo.
-- Regra + fatos. Disponibilidade nunca e armazenada, e calculada.

create extension if not exists btree_gist;

create table if not exists servicos (
  id             serial primary key,
  codigo         text unique,
  nome           text not null,
  descricao      text default '',
  preco_centavos integer not null,
  duracao_min    smallint not null,
  ativo          boolean default true,
  ordem          smallint default 0
);

-- O que esta incluso em cada servico. Vira a lista de bullets da vitrine.
create table if not exists servico_itens (
  id         serial primary key,
  servico_id integer not null references servicos(id) on delete cascade,
  ordem      smallint default 0,
  descricao  text not null
);

-- Acrescimo por porte do veiculo. O preco da tabela e para carro de passeio;
-- SUV e caminhonete somam um acrescimo por cima.
create table if not exists portes (
  codigo             text primary key,
  nome               text not null,
  acrescimo_centavos integer not null default 0,
  ordem              smallint default 0,
  ativo              boolean default true
);

create table if not exists horario_funcionamento (
  dia_semana smallint primary key,      -- 0 = domingo
  abre       time not null,
  fecha      time not null,
  qtd_boxes  smallint not null default 1,
  aberto     boolean default true
);

create table if not exists bloqueios (
  id      serial primary key,
  periodo tstzrange not null,
  motivo  text
);

create table if not exists agendamentos (
  id               serial primary key,
  codigo           text unique not null,
  cliente_nome     text not null,
  cliente_telefone text not null,
  veiculo_placa    text default '',      -- opcional: nem todo cliente sabe de cor
  veiculo_modelo   text default '',
  porte_codigo     text references portes(codigo),
  box              smallint not null,
  periodo          tstzrange not null,
  total_centavos   integer not null,
  status           text not null default 'pendente',
  payment_id       text,
  expira_em        timestamptz,
  criado_em        timestamptz default now(),

  -- A trava contra overbooking. A tela valida para ser gentil,
  -- a constraint valida para estar correto.
  -- 'expirado' entra no predicado porque a expiracao preguicosa
  -- (secao 6) libera o slot na leitura; sem isso a constraint
  -- continuaria segurando um carrinho abandonado.
  constraint sem_overbooking exclude using gist (
    box     with =,
    periodo with &&
  ) where (status not in ('cancelado', 'expirado'))
);

-- Item de pedido e foto, nao espelho: guarda nome, preco e duracao do dia
-- da compra. O acrescimo de porte entra aqui como uma linha com servico_id
-- nulo, entao o total continua sendo a soma dos itens.
create table if not exists agendamento_itens (
  id             serial primary key,
  agendamento_id integer references agendamentos(id) on delete cascade,
  servico_id     integer references servicos(id),
  nome_snapshot  text not null,
  preco_centavos integer not null,
  duracao_min    smallint not null
);

-- Galeria de trabalhos. O arquivo mora em midia/portfolio/, o banco guarda
-- so o nome e os metadados.
create table if not exists portfolio (
  id         serial primary key,
  arquivo    text unique not null,
  legenda    text default '',
  servico_id integer references servicos(id) on delete set null,
  ordem      smallint default 0,
  ativo      boolean default true,
  criado_em  timestamptz default now(),

  -- Os bytes ficam aqui, nao so no disco. Em hospedagem com disco
  -- efemero (Streamlit Cloud, por exemplo) a pasta some a cada deploy;
  -- o banco e quem faz a foto sobreviver, e o disco vira so cache.
  imagem     bytea,
  miniatura  bytea
);

create index if not exists agendamento_itens_ag_idx on agendamento_itens (agendamento_id);
create index if not exists servico_itens_srv_idx     on servico_itens (servico_id, ordem);
create index if not exists agendamentos_periodo_idx  on agendamentos using gist (periodo);
create index if not exists agendamentos_status_idx   on agendamentos (status, criado_em desc);
create index if not exists bloqueios_periodo_idx     on bloqueios using gist (periodo);
create index if not exists portfolio_ordem_idx       on portfolio (ativo, ordem, id desc);
