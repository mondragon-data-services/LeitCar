-- Catalogo real da Leite Estetica Automotiva (Duartina - SP).
-- Fonte: leite-estetica-especificacao.md, tabela manuscrita de 17/02/2022.
-- Precos base referentes a carro de passeio; SUV e caminhonete somam acrescimo.

insert into servicos (codigo, nome, descricao, preco_centavos, duracao_min, ativo, ordem) values
  ('simples', 'Lavagem simples',
   'O básico bem feito: seu carro limpo por dentro e por fora.',
   8000, 60, true, 1),
  ('detalhamento', 'Lavagem com detalhamento',
   'Acabamento nos detalhes, cera na pintura e selante nos pneus.',
   15000, 180, true, 2),
  ('completo', 'Detalhamento completo com higienização',
   'O serviço mais completo da casa. Leva o dia inteiro e devolve o carro como novo.',
   60000, 480, true, 3)
on conflict (codigo) do nothing;

insert into servico_itens (servico_id, ordem, descricao)
select s.id, v.ordem, v.descricao
from (values
  ('simples',      1, 'Limpeza interna sem detalhamento'),
  ('simples',      2, 'Lavagem externa'),
  ('simples',      3, 'Limpeza da caixa de rodas'),

  ('detalhamento', 1, 'Limpeza interna com detalhamento'),
  ('detalhamento', 2, 'Lavagem externa com detalhamento e cera'),
  ('detalhamento', 3, 'Limpeza da caixa de rodas'),
  ('detalhamento', 4, 'Selante nos pneus'),

  ('completo',     1, 'Higienização interna com detalhamento'),
  ('completo',     2, 'Limpeza de bancos, carpete, teto e lateral das portas'),
  ('completo',     3, 'Lavagem externa com detalhamento, descontaminação da pintura e cera'),
  ('completo',     4, 'Revitalização das partes plásticas externas'),
  ('completo',     5, 'Limpeza da caixa de rodas'),
  ('completo',     6, 'Selante nos pneus'),
  ('completo',     7, 'Remoção de chuva ácida dos vidros')
) as v(codigo, ordem, descricao)
join servicos s on s.codigo = v.codigo
where not exists (select 1 from servico_itens i where i.servico_id = s.id);

-- ATENCAO: os acrescimos de SUV e caminhonete sao placeholders.
-- A tabela manuscrita diz so "valor tem acrescimo", sem numero.
-- Trocar pelos reais no admin (pendencia 1 da especificacao).
insert into portes (codigo, nome, acrescimo_centavos, ordem, ativo) values
  ('carro',       'Carro',       0,    1, true),
  ('suv',         'SUV',         3000, 2, true),
  ('caminhonete', 'Caminhonete', 5000, 3, true)
on conflict (codigo) do nothing;

-- Domingo fechado, sabado ate as 13h (secao 3.2 da especificacao).
-- qtd_boxes = 1: "so um veiculo por slot". Com 1 box, o detalhamento
-- completo (8h) consome o dia inteiro sozinho, que e o comportamento
-- que a especificacao pede.
insert into horario_funcionamento (dia_semana, abre, fecha, qtd_boxes, aberto) values
  (0, '08:00', '12:00', 1, false),
  (1, '08:00', '18:00', 1, true),
  (2, '08:00', '18:00', 1, true),
  (3, '08:00', '18:00', 1, true),
  (4, '08:00', '18:00', 1, true),
  (5, '08:00', '18:00', 1, true),
  (6, '08:00', '13:00', 1, true)
on conflict (dia_semana) do nothing;
