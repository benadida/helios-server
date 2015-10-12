

# Guia de instalação e configuração do Helios

*This README is intended for Portuguese audience. *

Neste tutorial são descritos os principais passos para instalação de um servidor para disponibilização do Helios.

** Instalação servidor (Ubuntu) **

*Supondo uma máquina apenas com o sistema operacional*

Atualizações/instalações de pacotes:

sudo apt-get dist-upgrade
sudo apt-get install apache2
sudo apt-get install postgresql-9.3
sudo apt-get install postgresql-server-dev-9.3
sudo apt-get install python-dev
sudo apt-get install libsasl2-dev
sudo apt-get install libldap2-dev (*para o módulo de autenticação ldap*)
sudo apt-get install python-ldap (*para o módulo de autenticação ldap*)
sudo apt-get install gettext (*para tradução*)
sudo apt-get install libapache2-mod-wsgi
sudo apt-get install git (*se for baixar e/ou atualizar o código via github*)


### Configurações
#### Banco
*sudo su postgres*
*psql*
*create user helios;*
*create role helios with createdb createrole login;*
*alter user helios with password 'sua senha';*

Editar o arquiv **pg_hba.conf** e inserir a linha:

`local   all              helios                         md5` 

logo acima da linha

`local   all             all         peer`

A configuração acima corrige o seguinte erro:

> 
Exception Type: 	OperationalError
Exception Value: 	
FATAL:  Peer authentication failed for user "helios"


#### Obtenção do código-fonte e preparação da aplicação

Você pode baixar um zip com o fonte ou clonar o repositório. Supondo que o código vai ser baixado via git:

*git clone https://github.com/shirlei/helios-server.git*


Não é obrigatório, mas é uma boa prática, criar um ambiente virtual para a disponibilização do Helios, tanto para desenvolvimento quanto para implantação, pois isso permite separar as dependências do projeto e não interferir em outros sistemas na mesma máquina. 

Primeiramente, instale o pip, seguindo as orientações do desenvolvedor:
http://pip.readthedocs.org/en/stable/

Depois, instale o virtualenv, seguindo também as orientações disponíveis em:
http://virtualenv.readthedocs.org/en/latest/

Terminada a instalação do virtualenv,  dentro do diretório onde o helios foi baixado, basta dar o comando 
*virtualenv venv*

(venv é um exemplo, pode ser dado outro nome se necessário).

Para ativar o ambiente virtual, execute
*source venv/bin/activate*

Com o ambiente virtual ativado, instale os requisitos para a execução do helios:

`pip install -r requirements.txt`  

*ATENÇÃO: Utilize o requirements.txt deste repositório, para instalar o pacote django-auth-ldap e outros necessários às customizações realizadas. Lembrando também que apesar de se pretender manter este repositório atualizado com o do Ben Adida, não necessariamente vai ser simultâneo, então se você utilizar o dele, pode haver versões diferentes de pacotes.*

Após terminar a instalação dos pacotes necessários, é possível realizar as devidas execuções de banco de dados (criação de banco, tabelas, etc) executando o script reset.sh:

`$./reset.sh`

Se tiver algum problema rodando o script acima, provavelmente vai ser relacionado à configuração do PostgreSQL e, nesse caso, o *google é seu amigo.*

Para disponibilizar o helios em português, é preciso compilar os arquivos de tradução. Execute o seguinte comando a partir do diretório do Helios:

`python manage.py compilemessages`

Após a compilação, arquivos .mo devem ter sido gerados em locale/pt_BR/LC_MESSAGES

Maiores informações em https://docs.djangoproject.com/en/1.6/ref/django-admin/

Se tudo estiver correto até aqui, agora você pode rodar o servidor de desenvolvimento, distribuído com o django, e testar a instalação básica:

`$python manage.py runserver 0.0.0.0:8000` *# 0.0.0.0 para que fique acessível da rede. Pode executar até runserver, se preferir. Também pode trocar a porta!*

Em outro terminal, coloque o celery para rodar. Essa parte é importante, pois é ele quem vai gravar os votos, enviar emails, processar o arquivo de eleitores, etc!

`python manage.py celeryd`


## Servidor de Produção

O servidor descrito no tópico anterior é apenas para desenvolvimento, não deve ser usado em um ambiente de produção! 

É possível trabalhar com diversos servidores web, porém no caso em questão optou-se pelo [Apache](https://docs.djangoproject.com/en/1.6/topics/install/#install-apache-and-mod-wsgi).

--- Configuração apache ---
Módulos a serem habilitados, para a configuração exemplo:
sudo a2enmod rewrite
sudo a2enmod ssl

Para configurar o httpd.conf ou equivalente, siga as instruções em [How to use Django with Apache and mod_wsgi](https://docs.djangoproject.com/en/1.6/howto/deployment/wsgi/modwsgi/).


A parte de servir os arquivos estáticos é a mais trabalhosa. Essa configuração é necessária, porque no servidor de desenvolvimento, o django serve esses arquivos, porém, na produção, eles precisam ser configurados para serem servidos pelo servidor web.

Os arquivos 'tradicionais' são os de css, javascript e imagens. Para coletar esses arquivos, você deve executar o comando collectstatic, conforme descrito em [Collect static app](https://docs.djangoproject.com/en/1.6/ref/contrib/staticfiles//).

No caso do Helios em particular, há módulos sendo servido estaticamente (total ou parcial): o heliosbooth e o heliosverifier, os quais também precisam ser configurados.

No estágio atual, optei por uma solução feia, mas simples e que atendia ao curto prazo disponível, que foi a de fazer um link simbólico dos arquivos desses módulos para o diretório no qual coletei os demais arquivos estáticos (sitestatic). E então configurei *alias* para eles na configuração do apache:

Alias /booth /`<path_to_site>`/sitestatic

Alias /verifier /`<path_to_site>`/sitestatic


Maiores informações em:

https://docs.djangoproject.com/en/1.6/ref/django-admin//[]

#### Administração pelo site de administração do django

Ao rodar o reset.sh, você deve ter sido solicitado a criar um usuário de administração do django. Isso se deve ao fato de aplicação admin estar habilitada no settings.py (django.contrib.admin), pois iremos utilizá-la em algumas customizações feitas para este *fork* do helios.

Após finalizar a instalação, você deve entrar em http(s)://endereco-do-seu-servidor-helios/admin e se conectar com o usuário e senha de administração, cadastrados no passo descrito anteriormente. Após logar, será disponibilizada uma tela de administração, mostrando diversas apps habilitadas para essa tarefa. Localize a opção `Helios_Auth` e clique em *Users*. Na tela seguinte, escolha o usuário que quer editar, clicando no mesmo. Na tela de edição, marque a opção *Admin_p* e salve, caso você queira que o usuário em questão possa criar eleições ao se conectar no Helios.

Outra customização disponível, acessível por essa administração, é a opção de listar ou não uma eleição na página pública inicial do sistema. Se você quiser que uma eleição seja listada, na página inicial de administração, localize a opção `Helios` e clique em *Elections*. Na tela seguinte, clique no nome da eleição que você gostaria que fosse listada na página pública e na tela de edição, marque a opção *Featured p* e salve.

Para maiores informações da aplicação *django admin site*, visite https://docs.djangoproject.com/en/1.6/ref/contrib/admin/

#### Alguns lembretes:

As configurações de conexão e autenticação LDAP devem ser configuradas caso a caso. 
A documentação da biblioteca utilizada pode ser encontrada em:http://pythonhosted.org/django-auth-ldap/example.html
Ela não é muito completa, mas as configurações principais estão no settings.py e são `AUTH_LDAP_SERVER_URI`, `AUTH_LDAP_BIND_DN`, `AUTH_LDAP_BIND_PASSWORD`, e `AUTH_LDAP_USER_SEARCH`. AUTH_LDAP_BIND_DN e AUTH_LDAP_BIND_PASSWORD vão ter um valor configurado se o servidor LDAP exigir usuário e senha para fazer consultas. Ou seja, a configuração é caso a caso e uma leitura cuidadosa da documentação disponível no link do django-auth-ldap é recomendada, para outras dúvidas.

LEMBRAR DE ALTERAR EM SETTINGS.PY A CONSTANTE DEBUG DE TRUE PRA FALSE!

TROCAR [SECRET_KEY](https://docs.djangoproject.com/en/dev/ref/settings/#std:setting-SECRET_KEY) - não usar a do repositório. Há ferramentas na web pra isso, como a disponível em [http://www.miniwebtool.com/django-secret-key-generator/](http://www.miniwebtool.com/django-secret-key-generator/)

Conforme indicado no settings.py, na configuração de SECURE_URL_HOST, ela não deve ser mudada depois que você criar eleições (ao menos eleições reais), pois senão a URL de depósito de voto na eleição ficará inválida, pois esta informação é utilizada na geração da eleição.

A versão do Django utilizada nesta versão do Helios é a 1.6.10, sendo esta a principal fonte de consulta pra aprendizado sobre esta versão: https://docs.djangoproject.com/en/1.6/

--- Original Readme ---

# Helios Election System

Helios is an end-to-end verifiable voting system.

![Travis Build Status](https://travis-ci.org/benadida/helios-server.svg?branch=master)

[![Stories in Ready](https://badge.waffle.io/benadida/helios-server.png?label=ready&title=Ready)](https://waffle.io/benadida/helios-server)
