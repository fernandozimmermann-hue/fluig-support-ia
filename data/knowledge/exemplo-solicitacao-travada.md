---
title: Solicitacao de processo BPM travada em uma atividade
url: https://tdn.totvs.com/
---

# Solicitacao travada em uma atividade

Este documento e um EXEMPLO de formato, para validar a ingestao. Substitua o
conteudo por procedimentos reais validados pela equipe.

## Sintoma

O usuario relata que a solicitacao nao avanca: a atividade continua aparecendo
como pendente mesmo depois de o responsavel ter concluido a tarefa, ou nao
aparece na caixa de nenhum usuario.

## Causas mais comuns

1. **Responsavel sem atribuicao valida.** O mecanismo de atribuicao da atividade
   aponta para um grupo, papel ou usuario que ficou vazio, inativo ou sem o
   campo usado pela regra de atribuicao preenchido.
2. **Erro em evento de processo.** Um evento (`beforeTaskSave`, `afterTaskSave`,
   `beforeStateEntry`) lanca excecao e o fluxo nao completa a transicao. O erro
   costuma aparecer no log do servidor com o nome do evento na stack.
3. **Versao publicada diferente da esperada.** A solicitacao foi aberta em uma
   versao anterior do processo e segue o fluxo daquela versao, nao o da versao
   atual.
4. **Timer ou gateway mal configurado.** Uma condicao de gateway nunca e
   satisfeita e a solicitacao fica parada sem responsavel.

## Como diagnosticar

1. Confirme o estado atual da solicitacao: numero, atividade e responsavel.
2. Verifique se o responsavel calculado existe e esta ativo.
3. Procure no log do servidor a excecao proxima ao horario da ultima movimentacao.
4. Compare a versao do processo da solicitacao com a versao publicada.

## Observacao importante

Mover a solicitacao manualmente resolve o sintoma, nao a causa. Sempre registre
a causa antes de aplicar qualquer contorno, para que o mesmo chamado nao volte.
