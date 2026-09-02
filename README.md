# Leite Estética Automotiva

Site com agendamento online para a Leite Estética Automotiva, em Duartina - SP.

Arquitetura conforme [ARQUITETURA-lavacar-streamlit.md](ARQUITETURA-lavacar-streamlit.md):
um app Streamlit multipage servindo cliente e admin, Postgres como banco,
landing HTML estática para o Google. Catálogo e preços conforme
[leite-estetica-especificacao.md](leite-estetica-especificacao.md).

O conceito central: **não armazenamos horários disponíveis, só o que foi
ocupado**. O banco guarda a regra (`horario_funcionamento`) e os fatos
(`agendamentos`, `bloqueios`). Disponibilidade é subtração, calculada na hora.

## Rodar local

Não precisa de Python instalado — só Docker.

```
docker compose up -d
```

| URL | O que é |
|---|---|
| http://localhost:8501 | site do cliente — serviços → horário → comprovante |
| http://localhost:8501/?area=admin | admin, senha `lavacar123` |
| http://localhost:8080 | landing estática do SEO, gerada do banco |

Parar: `docker compose down`. Zerar o banco: `docker compose down -v`.

## Tabela de preços

Preço base é para carro de passeio; o porte do veículo soma um acréscimo,
como manda a especificação: `valorFinal = precoBase + porte.acrescimo`.

| Serviço | Duração | Carro | SUV | Caminhonete |
|---|---|---|---|---|
| Lavagem simples | 1h | R$ 80,00 | R$ 110,00 | R$ 130,00 |
| Lavagem com detalhamento | 3h | R$ 150,00 | R$ 180,00 | R$ 200,00 |
| Detalhamento completo com higienização | 8h | R$ 600,00 | R$ 630,00 | R$ 650,00 |

> **Os acréscimos de SUV e caminhonete são placeholders.** A tabela manuscrita
> diz apenas "valor tem acréscimo", sem número (pendência 1 da especificação).
> Corrija em **Admin → Tabela de preços → Acréscimo por porte** — a vitrine, a
> landing e os testes acompanham.

O que está incluso em cada serviço vive na tabela `servico_itens` e vira a
lista de itens do card. Edite em **Admin → Tabela de preços → O que está
incluso**.

## Portfólio

A galeria aparece na vitrine (12 fotos) e na landing do Google. Duas formas
de alimentar:

1. **Upload pelo admin** — `?area=admin` → **Portfólio** → *Enviar fotos*.
   Aceita várias de uma vez, em JPG, PNG, WEBP ou HEIC do iPhone.
2. **Largar na pasta** `fotos/` e clicar em *Importar tudo da pasta fotos/*
   na mesma tela.

Clicar numa foto abre ela em tamanho grande sobre a página, com a legenda.
O lightbox é CSS puro (`:target`), sem JavaScript — que o Streamlit remove do
markdown de qualquer jeito. Na landing, o clique abre a foto original em outra
aba. Fechar: no X, no fundo escuro ou no botão voltar do navegador.

Toda foto que entra é normalizada: orientação do EXIF aplicada (foto tirada
com o celular deitado não sai de lado), redimensionada para 1600 px e
recomprimida, mais uma miniatura de 640 px. As 27 fotos que você mandou
saíram de ~300 KB cada, com miniaturas de ~50 KB. Os arquivos ficam em
`static/portfolio/`, que o Streamlit serve por HTTP em `/app/static/`
(`enableStaticServing` no config), então o HTML da página fica leve.

O nome final do arquivo carrega um hash do conteúdo, então **importar duas
vezes não duplica a galeria**. Os originais ficam em `fotos/`, as versões
tratadas em `static/portfolio/`.

Na mesma tela dá para editar legenda, associar a um serviço, mudar a ordem,
esconder sem apagar e excluir de vez.

## Testes

```
docker compose exec app python -m pytest tests/ -q
```

35 testes. `test_agenda`, `test_precos`, `test_pix` e `test_portfolio` não
importam `streamlit`; `test_overbooking` precisa do banco e é pulado quando
`DATABASE_URL` não está definida.

`test_precos.py` trava a matriz 3×3 de preços contra a especificação — se
alguém mudar um acréscimo sem querer, o teste acusa.

## O que testar na mão

1. **Preços** — troque o porte entre Carro, SUV e Caminhonete: os três cards
   recalculam de uma vez. A URL vira `?porte=suv`, então o link já leva a
   escolha junto.
2. **Serviço** — o catálogo é de níveis: escolher um troca o anterior, não
   soma. A URL vira `?c=2x1&porte=suv` e sobrevive a refresh.
3. **Horários** — a grade respeita a duração. O detalhamento completo leva
   8h e, com 1 box, consome o dia inteiro: depois de marcado, não sobra
   horário naquele dia.
4. **Agendar** — o diálogo valida nome, WhatsApp e placa. O acréscimo de
   porte aparece como uma linha própria no comprovante.
5. **Portfólio** — suba uma foto no admin e recarregue a vitrine.
6. **Landing** — http://localhost:8080 tem a tabela de preços por porte, a
   galeria e o JSON-LD de `AutoWash`. Depois de mexer no admin, rode
   `docker compose exec app python landing/gerar_landing.py /app/landing/dist/index.html`.

## Pendências da especificação ainda abertas

Estão todas com placeholder no sistema, prontas para trocar sem mexer em código:

1. **Acréscimo real de SUV e caminhonete** — hoje R$ 30 e R$ 50 (Admin → Tabela de preços).
2. **Duração real de cada serviço** — hoje 1h / 3h / 8h (Admin → Tabela de preços).
3. **Quantos carros em paralelo** — hoje 1 box (Admin → Horários).
4. **Horário de funcionamento** — hoje seg-sex 8h–18h, sáb 8h–13h, dom fechado (Admin → Horários).
5. **Telefone e endereço** — hoje `14998904665` (número de testes) e "Duartina - SP" em `.streamlit/secrets.toml`.
6. **Sinal para o serviço de R$ 600** — o PIX está pronto e desligado (veja abaixo).

## Ligar o PIX (opcional)

Por padrão não há cobrança: o agendamento nasce `confirmado` e o cliente
paga na entrega. Para cobrar um sinal, preencha a chave em
`.streamlit/secrets.toml`:

```toml
[pix]
chave = "sua-chave-pix"
sinal_centavos = 2000
centavos_unicos = true
```

e reinicie (`docker compose restart app`). O pedido passa a nascer `pendente`
com 30 minutos para pagar, mostra o QR do BR Code montado offline (sem
gateway, sem taxa) e um botão "Já paguei" que abre o WhatsApp. O dono dá
baixa no admin. Os centavos são únicos por pedido, que é o que torna a
conciliação no extrato rápida — o `txid` não serve para isso em QR estático.

Passado o prazo sem baixa, o horário volta para a agenda sozinho:
expiração preguiçosa na leitura, sem cron e sem worker.

## Estrutura

```
app.py                    roteamento por query_params (?pedido=, ?area=admin, ?p=agendar)
paginas/                  telas — a única camada que seria jogada fora numa migração
servicos/
  agenda.py               horarios_livres — regra de negócio, não importa streamlit
  db.py                   st.connection e queries
  carrinho.py             serviço e porte espelhados em query_params
  portfolio.py            normalização e armazenamento das fotos
  pix.py                  BR Code EMV e CRC16, sem dependência externa
  formato.py              centavos, telefone, placa, código do pedido
  loja.py                 dados da loja e segredos
landing/gerar_landing.py  landing do SEO gerada do banco (cron diário)
sql/                      001_schema.sql, 002_seed.sql
fotos/                    pasta de depósito das fotos originais
static/portfolio/         fotos tratadas + miniaturas, servidas por HTTP (fora do git)
deploy/                   systemd, nginx, cron para a VM da Oracle Cloud
tests/
```

## Produção (seção 10 da arquitetura)

`deploy/` traz o `lavacar.service` (systemd, `Restart=always`, o app nunca
dorme), o `nginx.conf` com as linhas de `Upgrade` que o WebSocket do
Streamlit exige, e o `cron.txt` com a regeração da landing e o `pg_dump`
diário. HTTPS com Certbot nos dois domínios.

## Desvios conscientes dos documentos

- **A constraint `EXCLUDE`** usa `where (status not in ('cancelado',
  'expirado'))` em vez de só `<> 'cancelado'`. Sem o `'expirado'`, um
  carrinho abandonado continuaria travando o box no banco mesmo depois de a
  leitura já ter liberado o slot.
- **A grade de horários** é a da arquitetura (calculada pela duração, com
  boxes), não a grade fixa de 1 em 1 hora da especificação. A própria
  especificação lista isso como melhoria para a versão real, na seção 3.2 —
  e é o que faz o serviço de 8h ocupar o dia inteiro sozinho.
- **O acréscimo de porte** entra no pedido como um item com `servico_id`
  nulo. Assim o total continua sendo a soma dos itens e o comprovante mostra
  de onde veio a diferença de preço.
