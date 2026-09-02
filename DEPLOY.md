# Publicar no Streamlit Community Cloud

O app e o banco estao prontos. Falta so apontar um para o outro: o
Streamlit Cloud roda o Python, o Neon guarda os dados.

---

## Antes de começar: o que muda no Community Cloud

A `ARQUITETURA-lavacar-streamlit.md` (seção 2.1) recomenda **não** usar o
Community Cloud, e vale saber o que você está aceitando:

| | Community Cloud (grátis) | VM Oracle da arquitetura |
|---|---|---|
| Custo | R$ 0 | R$ 0 |
| Cold start | dorme depois de ~7 dias sem visita; primeira carga leva ~30s | nunca dorme |
| Latência | servidor nos EUA, ~130 ms por clique | São Paulo, ~10 ms |
| Banco | externo, por sua conta | Postgres na mesma máquina |
| Landing SEO | não hospeda (é Nginx) | hospeda |
| Trabalho para subir | 10 minutos | uma tarde |

Para um lava car de bairro o cold start é o ponto sensível: o cliente
clica no link do WhatsApp às 21h e encara tela branca por meio minuto.
Como primeiro ar, para validar com o Leite, está ótimo. Quando virar o
canal de venda de verdade, a VM da Oracle é o passo seguinte — e nada do
código muda, só o lugar onde roda.

---

## 1. O banco — já está pronto

Projeto Neon `polished-rice-69091972`, branch `production`, PostgreSQL 18
em `us-east-2`, plano grátis. Já foi tudo aplicado e conferido contra ele:

- as 8 tabelas e o catálogo (3 serviços, 3 portes, 14 itens, 7 dias);
- as 27 fotos do portfólio, com legenda e ordem (6,7 MB);
- a constraint `EXCLUDE` de overbooking, testada com duas reservas
  simultâneas no mesmo box — a segunda foi recusada pelo banco.

A connection string fica no console, em **Connect**. Prefira a versão
*pooled* (o host tem `-pooler` no nome), que é a adequada para o
Streamlit, que abre várias sessões.

> Se um dia trocar de banco: o app cria schema e catálogo sozinho no
> primeiro acesso. Ele confere quais tabelas existem e só roda o DDL
> quando falta alguma, então isso não custa nada nos boots seguintes.
> Qualquer Postgres 14+ com SSL serve.

## 2. Subir o app (3 min)

1. Entre em [share.streamlit.io](https://share.streamlit.io) com a conta
   do GitHub que tem acesso ao repositório.
2. **New app** → repositório `mondragon-data-services/LeitCar`, branch
   `main`, arquivo principal `app.py`.
3. Em **Advanced settings**, escolha **Python 3.12** e cole os secrets
   (o conteúdo abaixo, com seus valores).
4. **Deploy**.

> No plano gratis o Neon suspende o compute depois de alguns minutos sem
> consulta. A primeira visita depois disso paga uns 4s a mais para acordar
> o banco; as seguintes respondem em meio segundo.

## 3. Secrets

Cole em *Advanced settings → Secrets*, ou depois em *Settings → Secrets*.
É o mesmo formato do `.streamlit/secrets.toml`, que **não** vai para o
repositório.

```toml
[connections.postgresql]
url = "postgresql://usuario:senha@host.neon.tech/neondb?sslmode=require"

[admin]
senha = "escolha-uma-senha-forte"

[loja]
nome = "Leite Estética Automotiva"
telefone = "14998904665"
endereco = "Duartina - SP"
cidade = "Duartina"
chamada = "Lavagem, detalhamento e higienização com acabamento de loja especializada."
url_publica = "https://SEU-APP.streamlit.app"
url_site = "https://SEU-APP.streamlit.app"

# Deixe a chave vazia para não cobrar nada (pagamento na entrega).
[pix]
chave = ""
nome = "LEITE ESTETICA AUTOMOTIVA"
cidade = "DUARTINA"
sinal_centavos = 2000
centavos_unicos = true
```

Depois do primeiro deploy você descobre a URL do app. Volte nos secrets e
corrija `url_publica` — é ela que vai no link do comprovante que o cliente
recebe no WhatsApp.

## 4. As fotos ja estao la

As 27 fotos foram importadas para o Neon com legenda e ordem, entao a
galeria aparece assim que o app sobe.

Para subir mais: `?area=admin` -> **Portfolio** -> *Enviar fotos*. Se um
dia precisar recomecar do zero, os originais estao versionados em
`fotos/` e o botao *Importar tudo da pasta* reconstroi a galeria.

---

## Por que as fotos aguentam o redeploy

O disco do Community Cloud é efêmero: a cada deploy ou reinício, tudo que
foi gravado em `static/` desaparece. Se as fotos morassem só no disco, a
galeria voltaria vazia toda vez que o Leite subisse uma foto nova e o app
reiniciasse.

Por isso os bytes de cada foto ficam **no Postgres** (`portfolio.imagem` e
`portfolio.miniatura`), e o disco é só um cache: quando a vitrine percebe
que falta um arquivo, `db.materializar_fotos()` reescreve a partir do
banco. Isso foi testado apagando `static/portfolio/` inteiro — na carga
seguinte as 27 fotos voltaram sozinhas.

O custo é uns 250 KB por foto no banco. Para um portfólio de lava car,
irrelevante.

## O que não vai junto

- **A landing estática do SEO** (`landing/`) precisa de Nginx e fica de
  fora. Enquanto isso o app não é indexável pelo Google — é o problema da
  seção 2.5 da arquitetura, que só se resolve com a VM. Se quiser SEO
  antes disso, publique o HTML gerado em qualquer host estático grátis
  (GitHub Pages, Netlify) apontando o botão "Agendar agora" para o app.
- **O `docker-compose.yml`** continua no repositório, para desenvolvimento
  local. O Streamlit Cloud ignora.

## Rodar local continua igual

```
docker compose up -d
```

Nada do que foi feito para a nuvem quebrou o ambiente local: o mesmo
código lê `DATABASE_URL` (Docker) ou os secrets (nuvem).
