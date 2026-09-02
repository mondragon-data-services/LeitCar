# Lava Car Online :: Arquitetura Streamlit

Documento de referência para implementar com Claude Code.
Stack 100% Python, um único app Streamlit, um banco Postgres.

Este documento assume que você já conhece as limitações do Streamlit para site público. A seção 2 mostra o contorno de cada uma. As demais seções são a implementação.

---

## 1. Visão geral em uma frase

**Streamlit** multipage servindo cliente e admin, **Postgres** como banco, hospedado numa **VM da Oracle Cloud em São Paulo** com Nginx na frente, mais uma **landing page HTML estática** só para o Google enxergar.

Custo: R$ 0 de infraestrutura. Só o domínio, perto de R$ 40 por ano.

---

## 2. As seis limitações e o contorno de cada uma

Esta é a seção mais importante do documento. Leia antes de escrever qualquer código.

### 2.1 Cold start

**Problema:** no Streamlit Community Cloud o app dorme após um tempo parado. O cliente clica no link do WhatsApp às 21h e encara tela branca por 30 segundos.

**Contorno:** não use o Community Cloud. Suba numa VM Always Free da Oracle Cloud, região São Paulo, com `systemd` mantendo o processo vivo. O app nunca dorme e a latência cai de 130 ms para cerca de 10 ms.

Esse contorno resolve dois problemas de uma vez, porque o Streamlit é conversador: ele faz round trip a cada interação. Latência baixa é o que separa "parece travado" de "parece instantâneo".

### 2.2 Carrinho perdido no refresh

**Problema:** `st.session_state` vive na memória do servidor e amarrado à conexão WebSocket. Refresh, queda de sinal no celular ou troca de rede e o carrinho evapora.

**Contorno:** espelhe o carrinho em `st.query_params`. A URL vira a fonte da verdade e sobrevive a tudo, inclusive ao cliente compartilhar o link.

```python
def carregar_carrinho() -> dict[str, int]:
    """Le o carrinho da URL. Formato: ?c=3x1,7x2"""
    bruto = st.query_params.get("c", "")
    itens = {}
    for parte in filter(None, bruto.split(",")):
        sid, qtd = parte.split("x")
        itens[sid] = int(qtd)
    return itens


def salvar_carrinho(itens: dict[str, int]) -> None:
    if itens:
        st.query_params["c"] = ",".join(f"{k}x{v}" for k, v in itens.items())
    else:
        st.query_params.pop("c", None)
    st.session_state.carrinho = itens
```

Regra: `session_state` é cache rápido, `query_params` é persistência. Escreva nos dois, leia do `query_params` quando o `session_state` estiver vazio.

### 2.3 Rerun a cada clique

**Problema:** o Streamlit reexecuta o script inteiro a cada interação. Adicionar um item ao carrinho recarrega a lista de serviços e recalcula os slots. Pisca e parece lento.

**Contorno:** `@st.fragment`. Ele isola um pedaço da página e só reexecuta aquele pedaço.

```python
@st.fragment
def bloco_carrinho():
    """So este bloco reroda quando o usuario mexe no carrinho."""
    itens = carregar_carrinho()
    ...
```

Combine com `@st.cache_data` no catálogo e nos horários de funcionamento, que quase nunca mudam:

```python
@st.cache_data(ttl=300)
def listar_servicos():
    return pd.read_sql("select * from servicos where ativo order by ordem", conn)
```

Com fragment mais cache, o app fica indistinguível de uma SPA para o volume de um lava car.

### 2.4 Webhook de pagamento

**Problema:** Streamlit não expõe rota HTTP. Não tem como receber o POST de confirmação de um gateway.

**Contorno:** não use gateway. **PIX estático gerado offline**, com confirmação manual pelo dono no admin.

O código do PIX copia e cola é apenas uma string no padrão EMV BR Code, definido pelo Banco Central. Você monta ela em Python puro, sem API, sem conta de gateway e sem taxa. O dinheiro cai direto na conta do lava car.

```python
def montar_brcode(chave: str, nome: str, cidade: str,
                  valor: Decimal, txid: str) -> str:
    """Gera o payload EMV do PIX estatico. Sem internet, sem gateway."""
    def campo(cid: str, valor: str) -> str:
        return f"{cid}{len(valor):02d}{valor}"

    mai = campo("00", "br.gov.bcb.pix") + campo("01", chave)
    payload = (
        campo("00", "01")
        + campo("26", mai)
        + campo("52", "0000")
        + campo("53", "986")
        + campo("54", f"{valor:.2f}")
        + campo("58", "BR")
        + campo("59", nome[:25])
        + campo("60", cidade[:15])
        + campo("62", campo("05", txid[:25]))
    )
    return payload + "6304" + crc16(payload + "6304")
```

O `crc16` é o CCITT FFFF, umas 10 linhas. Se preferir não escrever à mão, a biblioteca `pix-utils` faz isso. Para virar imagem, `qrcode` mais `st.image`.

**Como o dono sabe quem pagou.** Essa é a parte que exige um truque, porque sem gateway ninguém avisa o sistema. Duas opções, da mais simples para a mais robusta:

1. O cliente paga, clica em "Já paguei" e é levado ao WhatsApp com uma mensagem pronta contendo o código do pedido e o comprovante. O dono confere no app do banco e confirma no admin. Simples e transparente.
2. Some centavos únicos ao valor. O pedido `LC7F3K` de R$ 89,00 vira R$ 89,07, com os centavos derivados do código. No extrato do banco cada valor é único, e o dono bate o pedido em segundos.

O campo `txid` do BR Code carrega o código do pedido, mas **não confie nele para conciliação**: em QR estático a exibição desse campo varia de banco para banco. O valor único da opção 2 é bem mais confiável.

**Sugestão para começar:** cobre só um sinal de R$ 20 ou nem cobre nada, com pagamento na hora da entrega. O PIX antecipado serve para reduzir no show, não para faturar. Se o lava car não tem problema de gente furando horário, pule o pagamento inteiro na versão 1.

Quando o volume justificar, o Mercado Pago entra por polling com `st.fragment(run_every="4s")` sem mudar nada do resto da arquitetura, porque o modelo de status do agendamento já está pronto para isso.

### 2.5 SEO zero

**Problema:** o Streamlit renderiza via WebSocket. O Google não indexa nada.

**Contorno:** uma página HTML estática de verdade servida pelo próprio Nginx na raiz do domínio, com o app no subdomínio ou numa subpasta.

```
lavacar.com.br          ->  index.html estatico, indexavel, com preços e endereço
agendar.lavacar.com.br  ->  o app Streamlit
```

A landing tem uma página só: nome, endereço, telefone, tabela de serviços, JSON LD de `LocalBusiness` e um botão grande "Agendar agora". É o que o Google precisa ver. O app não precisa ser indexado, ele precisa ser encontrado pelo botão.

Bônus: gere essa landing a partir do banco com um comando `python gerar_landing.py` rodando no cron diário. Preço mudou no admin, a landing atualiza sozinha.

### 2.6 URL de pedido

**Problema:** não existe rota `/pedido/LC7F3K`.

**Contorno:** `st.query_params` resolve. `?pedido=LC7F3K` funciona igual, é linkável e cabe no WhatsApp.

```python
if codigo := st.query_params.get("pedido"):
    mostrar_comprovante(codigo)
    st.stop()
```

---

## 3. Stack

| Camada | Escolha |
|---|---|
| App | Streamlit 1.4x com `st.navigation` |
| Banco | PostgreSQL 16 na mesma VM |
| Acesso a dados | `st.connection("postgresql")` com SQLAlchemy |
| Cache | `st.cache_data` e `st.cache_resource` |
| Isolamento de rerun | `@st.fragment` |
| Persistência de carrinho | `st.query_params` |
| Auth do admin | senha em `st.secrets` mais `st.session_state` |
| Landing SEO | HTML estático gerado por script, servido pelo Nginx |
| Proxy | Nginx com WebSocket habilitado |
| Processo | systemd |
| Host | Oracle Cloud Always Free, São Paulo |
| Pagamento | PIX estático (BR Code gerado offline), baixa manual no admin |
| Notificação | link `wa.me` |

---

## 4. O conceito central do projeto

### Não armazene horários disponíveis. Armazene apenas o que foi ocupado.

O banco guarda a **regra** (horário de funcionamento) e os **fatos** (agendamentos). Disponibilidade é calculada na hora, nunca guardada.

Analogia: um hotel não cadastra "quarto 101 livre dia 5, livre dia 6". Ele cadastra que o quarto existe e quem reservou. O resto é subtração.

Isso vale igual em Django, em Next.js ou em Streamlit. É decisão de modelagem, não de framework.

---

## 5. Schema

```sql
create extension if not exists btree_gist;

create table servicos (
  id             serial primary key,
  nome           text not null,
  descricao      text default '',
  preco_centavos integer not null,
  duracao_min    smallint not null,
  ativo          boolean default true,
  ordem          smallint default 0
);

create table horario_funcionamento (
  dia_semana smallint primary key,      -- 0 = domingo
  abre       time not null,
  fecha      time not null,
  qtd_boxes  smallint not null default 1,
  aberto     boolean default true
);

create table bloqueios (
  id      serial primary key,
  periodo tstzrange not null,
  motivo  text
);

create table agendamentos (
  id               serial primary key,
  codigo           text unique not null,
  cliente_nome     text not null,
  cliente_telefone text not null,
  veiculo_placa    text not null,
  veiculo_modelo   text default '',
  box              smallint not null,
  periodo          tstzrange not null,
  total_centavos   integer not null,
  status           text not null default 'pendente',
  payment_id       text,
  expira_em        timestamptz,
  criado_em        timestamptz default now(),

  constraint sem_overbooking exclude using gist (
    box     with =,
    periodo with &&
  ) where (status <> 'cancelado')
);

create table agendamento_itens (
  id             serial primary key,
  agendamento_id integer references agendamentos(id) on delete cascade,
  servico_id     integer references servicos(id),
  nome_snapshot  text not null,
  preco_centavos integer not null,
  duracao_min    smallint not null
);

create index on agendamentos using gist (periodo);
create index on agendamentos (status, criado_em desc);
```

Três decisões que valem explicação:

**Preço em centavos inteiros.** Float com dinheiro produz 29.989999999. Inteiro nunca erra.

**`tstzrange` em vez de dois campos.** O Postgres entende sozinho que dois intervalos colidem, com o operador `&&`. Com `inicio` e `fim` separados você reescreve essa lógica na mão toda vez.

**Snapshot de nome e preço no item.** Reajuste em janeiro não pode alterar o pedido de dezembro. Item de pedido é foto, não espelho.

### A trava contra overbooking

A constraint `EXCLUDE` acima é o que impede dois clientes de pegarem o mesmo horário no mesmo segundo.

No Streamlit isso é **mais crítico** que nos outros frameworks, não menos. O modelo de rerun faz o app reexecutar muito, e é fácil escrever um `if slot_livre: inserir` que roda duas vezes. A constraint não tem janela de corrida:

```python
try:
    with conn.session as s:
        s.execute(text("insert into agendamentos ..."), params)
        s.commit()
except IntegrityError as e:
    if "sem_overbooking" in str(e):
        st.error("Esse horário acabou de ser preenchido. Escolha outro.")
        st.cache_data.clear()
        st.rerun()
    raise
```

Regra prática: **a tela valida para ser gentil, a constraint valida para estar correto.** Precisa das duas.

---

## 6. Cálculo dos horários livres

Fica em `servicos/agenda.py`, fora da interface. Entrada: data e duração total do carrinho.

```python
def horarios_livres(data: date, duracao_min: int, antecedencia_min: int = 60):
    cfg = buscar_config(data.weekday_iso())
    if not cfg or not cfg.aberto:
        return []

    tz = ZoneInfo("America/Sao_Paulo")
    abre = datetime.combine(data, cfg.abre, tzinfo=tz)
    fecha = datetime.combine(data, cfg.fecha, tzinfo=tz)
    duracao = timedelta(minutes=duracao_min)
    limite = datetime.now(tz) + timedelta(minutes=antecedencia_min)

    ocupados = buscar_ocupados(abre, fecha)   # ignora cancelado e pendente vencido
    bloqueios = buscar_bloqueios(abre, fecha)

    livres, atual = [], abre
    while atual + duracao <= fecha:
        fim = atual + duracao
        if atual >= limite:
            colide = any(b.lower < fim and b.upper > atual for b in bloqueios)
            ocupacao = sum(1 for o in ocupados if o.lower < fim and o.upper > atual)
            if not colide and ocupacao < cfg.qtd_boxes:
                livres.append(atual)
        atual += timedelta(minutes=15)
    return livres
```

O `buscar_ocupados` filtra `status <> 'cancelado'` e descarta pendentes com `expira_em < now()`. É assim que o carrinho abandonado libera o slot sozinho, sem cron e sem worker. **Expiração preguiçosa resolve 90% dos casos que as pessoas montam fila para resolver.**

Exemplo concreto:
Loja das 8h às 18h, 2 boxes. Carrinho com Lavagem Completa (60 min) e Cera (30 min), total **90 minutos**.
Já existem um carro das 9h às 10h30 no box 1 e outro das 9h30 às 10h no box 2.
O slot das 9h30 cai fora, os 2 boxes estão ocupados.
O slot das 10h30 entra.
O slot das 17h cai fora, porque 17h mais 90 minutos passa das 18h.

**Atenção:** a duração muda conforme o carrinho. Sempre recalcule os slots quando o carrinho mudar, senão você vende um slot de 30 minutos para um serviço de 2 horas.

---

## 7. Estrutura do projeto

```
lavacar/
  app.py                      st.navigation e roteamento por query_params
  paginas/
    vitrine.py                catalogo + carrinho
    agendar.py                data, slots, dados do cliente
    pagamento.py              QR do PIX e botao "Ja paguei"
    comprovante.py            ?pedido=LC7F3K
    admin_agenda.py
    admin_servicos.py
    admin_horarios.py
  servicos/
    db.py                     st.connection e queries
    agenda.py                 horarios_livres
    carrinho.py               query_params
    pix.py                    BR Code EMV e CRC16, sem dependencia externa
    formato.py                centavos, telefone, placa
  landing/
    gerar_landing.py
    template.html
  sql/
    001_schema.sql
    002_seed.sql
  deploy/
    lavacar.service
    nginx.conf
  .streamlit/
    config.toml
    secrets.toml              fora do git
  requirements.txt
```

---

## 8. Roteamento sem rotas

O Streamlit não tem URL de verdade, então o `app.py` decide o que mostrar lendo os query params:

```python
st.set_page_config(page_title="Lava Car", layout="centered",
                   initial_sidebar_state="collapsed")

if codigo := st.query_params.get("pedido"):
    comprovante.render(codigo)
    st.stop()

if st.query_params.get("area") == "admin":
    if not autenticado():
        tela_login()
        st.stop()
    pg = st.navigation([
        st.Page(admin_agenda.render,   title="Agenda"),
        st.Page(admin_servicos.render, title="Serviços"),
        st.Page(admin_horarios.render, title="Horários"),
    ])
    pg.run()
    st.stop()

vitrine.render()
```

Esconder a sidebar no fluxo do cliente é importante. Ela entrega que aquilo é um Streamlit e confunde quem só quer agendar um carro.

---

## 9. Deixar com cara de site, não de dashboard

Streamlit tem cara de ferramenta interna por padrão. Quatro ajustes resolvem quase tudo:

**`.streamlit/config.toml`**
```toml
[theme]
primaryColor = "#1d4ed8"
backgroundColor = "#ffffff"
font = "sans serif"

[client]
toolbarMode = "minimal"
showErrorDetails = false
```

**Esconder o menu e o rodapé** com um `st.markdown` de CSS no topo do app.

**`layout="centered"`** em vez de `wide`, porque a maioria dos clientes entra pelo celular.

**Um cabeçalho próprio** com logo e telefone em `st.columns`, para a primeira dobra não parecer um relatório.

---

## 10. Deploy na Oracle Cloud

**VM:** Ampere A1, Ubuntu 24.04, região São Paulo. O free tier ARM foi reduzido em junho de 2026 para 2 OCPUs e 12 GB, o que ainda é muito mais do que este projeto consome.

**Nginx.** O ponto crítico é o WebSocket. Sem estas linhas o Streamlit fica reconectando para sempre:

```nginx
server {
    server_name agendar.lavacar.com.br;
    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400;
    }
}

server {
    server_name lavacar.com.br;
    root /var/www/landing;      # a landing estatica do SEO
    index index.html;
}
```

**systemd** em `/etc/systemd/system/lavacar.service` com `Restart=always`, rodando `streamlit run app.py --server.port 8501 --server.address 127.0.0.1 --server.headless true`.

**HTTPS** com Certbot nos dois domínios.

**Postgres local** na mesma VM. Backup com `pg_dump` diário no cron mandando para o Object Storage da própria Oracle, que também é grátis.

---

## 11. Roteiro de implementação

**Fase 1: base**
VM provisionada, Postgres instalado, `sql/001_schema.sql` e `002_seed.sql` aplicados. `servicos/db.py` com `st.connection`. App mínimo listando serviços.

**Fase 2: vitrine e carrinho**
`servicos/carrinho.py` com o espelhamento em `query_params`. Cards de serviço com `@st.fragment`. Rodapé fixo com total e duração.

**Fase 3: agenda**
`servicos/agenda.py` com testes. Seletor de data. Grade de horários em fragment que reage à duração do carrinho.

**Fase 4: checkout**
`st.dialog` com nome, telefone e placa. Inserção transacional escolhendo o primeiro box livre. Tratamento de `IntegrityError`. Comprovante com código e botão do WhatsApp.

**Fase 5: admin**
Login por senha em `st.secrets`. Agenda do dia com `st.dataframe`. `st.data_editor` para serviços e horários. Ações de concluir e cancelar.

**Fase 6: acabamento**
Tema, CSS, sidebar escondida, `gerar_landing.py` e cron.

**Fase 7: PIX (opcional)**
`servicos/pix.py` com `montar_brcode` e `crc16`, mais teste comparando com um payload conhecido. Tela de pagamento com QR, botão de copiar e botão "Já paguei" que leva ao WhatsApp. No admin, ação de dar baixa mudando o status para confirmado.

Chave PIX, nome do recebedor e cidade ficam em `st.secrets`, nunca no código.

---

## 12. Testes que valem a pena

Escreva com pytest, sobre `servicos/agenda.py`, sem envolver o Streamlit:

1. Slot que ultrapassa o fechamento não aparece.
2. Com 2 boxes e 2 agendamentos sobrepostos, o slot some.
3. Dois inserts no mesmo box e horário levantam `IntegrityError`.
4. Pendente vencido deixa de ocupar o slot.

A lógica de negócio não deve importar nada de `streamlit`. Se importar, você não consegue testar sem subir o app.

---

## 13. Como usar este documento com o Claude Code

Salve como `ARQUITETURA.md` na raiz e vá por fase.

```
Leia ARQUITETURA.md. Implemente a Fase 1: sql/001_schema.sql com o schema
da secao 5 incluindo a constraint EXCLUDE, sql/002_seed.sql com 5 servicos
de lava car e o horario de segunda a sabado, e servicos/db.py usando
st.connection. Nao implemente telas ainda.
```

```
Leia ARQUITETURA.md. Implemente a Fase 3. A funcao horarios_livres deve
ficar em servicos/agenda.py sem importar streamlit, e vir com os quatro
testes da secao 12.
```

Peça para ele parar ao fim de cada fase e teste antes de seguir.

---

## 14. Quando reconsiderar

O Streamlit vai bem aqui. Mas se algum destes aparecer, é sinal de que o projeto passou do ponto:

* Mais de 30 pessoas usando ao mesmo tempo. Cada sessão é um processo com estado na memória.
* Necessidade de app mobile ou de integrar com outro sistema por API.
* Segunda unidade do lava car com catálogo e agenda separados.
* O dono querendo mexer no visual sem depender de você.

Nesse dia, o schema, a função `horarios_livres` e as regras de negócio migram inteiros. Só a camada de tela é jogada fora. Por isso a seção 12 insiste em não importar `streamlit` dentro de `servicos/`.
