# README - Versão em português

*This README is intended for portuguese native speakers. If you are interested in the original one, see README.txt*


Nesse tutorial descrevo alguns dos problemas enfrentados durante a customização desse projeto de modo geral, desde problemas de instalação e configuração, até algumas decisões de alteração.

** Para começar, leia o README.txt e o INSTALL.md **

# Obtenção do código-fonte

Você pode baixar um zip com o fonte, clonar o repositório ou fazer um fork. Se não está familiarizado com o Git, um bom lugar para começar é [por aqui](https://help.github.com/articles/set-up-git, "Set Up Git").


# Configuração do ambiente de desenvolvimento

No INSTALL.md, se orienta a configuração de ambiente virtual utilizando o virtualenv. Não é obrigatório, mas é uma boa prática para isolar o ambiente de desenvolvimento e não interferir em outros projetos na mesma máquina.

Comecei o meu ambiente em um ambiente com o Ubuntu 13.10. Precisei instalar alguns pacotes:



* sudo apt-get install python-dev

* sudo apt-get install libsasl2-dev

* sudo apt-get install libldap2-dev *# com o objetivo de criar o módulo de autenticação ldap*


* sudo apt-get install python-ldap *# com o objetivo de criar o módulo de autenticação ldap*

* sudo apt-get install gettext *# para tradução*

* sudo apt-get install libapache2-mod-wsgi *#se usar o apache*

Também é necessário ter o postgres instalado e configurado para acesso pelo Helios.

No meu ambiente de desenvolvimento, fiz uma configuração básica apenas para atender a necessidade de desenvolvimento, como segue:


* apt-get install postgresql-9.1 postgresql-server-dev-9.1

```
$ sudo -u postgres createuser helios



Shall the new role be a superuser? (y/n) y

create role helios with createdb createrole login;

 
alter user helios with password 'password';
```

Desnecessário dizer, mas substituir *password* com a senha desejada.



Editar o arquiv **pg_hba.conf** e inserir a linha:

`local   all              helios                            md5` 

logo acima da linha

`local   all             all         peer`

Se ainda não instalou, instale o [pip](http://pip.readthedocs.org/en/latest/installing.html, "pip install").


Para configurar o virtualenv, a [documentação oficial](http://virtualenv.readthedocs.org/en/latest/virtualenv.html#installation,"virtualenv documentation") é a melhor opção.


Com o ambiente virtual ativado, instale os requisitos para a execução do helios:

`pip install -r requirements.txt`

Instalação do rabbitmq-server (https://www.rabbitmq.com/install-debian.html):

`sudo apt-get install rabbitmq-server`

Execute o script reset.sh:
`$./reset.sh`

Se tiver algum problema rodando o script acima, provavelmente vai ser relacionado à configuração do PostgreSQL e, nesse caso, o *google é seu amigo.*

Agora você pode rodar o servidor de desenvolvimento, distribuído com o django, e testar a instalação básica:

`$python manage.py runserver 0.0.0.0:8000` *# 0.0.0.0 para que fique acessível da rede. Pode executar até runserver, se preferir. Também pode trocar a porta!*

Em outro terminal, coloque o celery para rodar. Essa parte é importante, pois é ele quem vai gravar os votos!

`python manage.py celeryd`