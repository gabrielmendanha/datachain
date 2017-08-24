# DataChain: assegurando a propriedade e imutabilidade de documentos digitais

Este projeto utiliza o BigchainDB + IPFS
como um repositório e sistema de trocas para documentos digitais
e foi apresentado como requisito parcial para a obtenção do grau de bacharelado
em Engenharia de Software
pela Universidade Federal do Ceará, campus Quixadá.


[Leia](http://www.repositoriobib.ufc.br/00003a/00003ad4.pdf) o trabalho de conclusão
de curso para
maiores detalhes.

## Começando

Baixe e instale o [go-ipfs](https://github.com/ipfs/go-ipfs) (v0.4.10), siga as instruções do
[site](https://dist.ipfs.io/#go-ipfs).

```
$ git clone https://github.com/gabrielmendanha/tcc2.git 
$ cd tcc2
$ pip3 install -r requirements.txt
```

##### Configure o BigchainDB
```
$ bigchaindb -y configure rethinkdb
```

##### Inicialize os serviços necessários **nesta ordem**

```
$ ipfs daemon
$ rethinkdb
$ bigchaindb start
```

##### Finalmente
```
$ export FLASK_APP=application.py
$ flask run
```


