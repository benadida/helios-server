# Guia de instalação e configuração do Helios

> This README is intended for Portuguese audience
> 
> Este é um repositório particular em que novas funcionalidades, atualizações e outras atividades de interesse particular ou de pesquisa são realizadas. 
> 
> Se você está interessado em informações sobre o repositório de uso no IFSC (http://www.ifsc.edu.br), por favor acesse https://github.com/ifsc/helios-server

Neste tutorial são descritos os principais passos para disponibilização do Helios em um servidor com a distribuição Linux Ubuntu (testado nas versões LTS 14.04, 16.04 e 18.04), embora já tenha sido feita instalação com sucesso no CentOS. 

Para seguir esse tutorial é necessário tenha alguma experiência com administração de sistemas Linux (instalação de pacotes, configuração de serviços, etc.).

## Personalizações feitas no Helios

Esse repositório contém as personalizações feitas no Helios. Ainda assim, buscará o sincronismo periódico com (sempre que possível e dentro do tempo possível) o projeto original do [Ben Adida](https://github.com/benadida/helios-server).

Personalizações e contribuições que fizemos que estão aqui e que não foram para o *upstream*:
- Tradução da interface para português
- Melhorias em algumas páginas e adequação para serem responsivas
- Criação de manuais para eleitores e para gestores de eleição
- Módulo de autenticação LDAP
- Módulo de autenticação Shibboleth
- Ajustes na página inicial e interface de administração para operação do Helios em ambiente Federado (Ex: Federação CAFe)
- Esse próprio arquivo com instruções para instalação do Helios :smile:

Publicamos dois artigos sobre essas personalizações:

- CHAVES, S. A., MELLO, E. R. Adoção de modelo controle acesso baseado em atributos em sistema de votação online para ofertá-lo como um serviço de TIC federado. In: WGID - Workshop de Gestão de Identidade, 2015, Florianópolis. XV Simpósio Brasileiro em Segurança da Informação e de Sistemas Computacionais. 
- CHAVES, S. A., MELLO, E. R. O uso de um sistema de votação on-line para escolha do conselho universitário In: WTE - Workshop de Tecnologia Eleitoral, 2014, Belo Horizonte. XIV Simpósio Brasileiro em Segurança da Informação e de Sistemas Computacionais 


## Instalação dos pacotes necessários (Ubuntu 18.04)

### Softwares necessários

* python2.7
* apache2
* libapache2-mod-wsgi
* postgresql e postgresql-contrib 
  * [Aqui tem um bom tutorial](https://www.digitalocean.com/community/tutorials/how-to-install-and-use-postgresql-on-ubuntu-18-04) de como instalar no Ubuntu 18.04
* build-essential
* git
* gettext 
  * para uso das funcionalidade de compilação de mensagens traduzidas
* python-pip
* python-ldap python-dev libsasl2-dev libldap2-dev
  * para utilização do módulo de autenticação LDAP

Para instalação dos pacotes apresentados acima foi necessário editar o arquivo  `/etc/apt/sources.list` e adicionar na seguinte linha a opção `universe`

```bash
deb http://archive.ubuntu.com/ubuntu bionic main universe
```

Depois é só fazer um `sudo apt update` e instalar os pacotes apresentados acima com o `sudo apt install`

> A versão do Django utilizada nesta versão do Helios é a [1.8.18](https://docs.djangoproject.com/en/1.8/).

## Preparação do ambiente para instalação do Helios

Recomendo que crie um usuário no sistema específico para o helios, por exemplo, usuário `helios`. 

### Configuração do banco de dados PostgreSQL

Editar o arquivo `pg_hba.conf` e inserir a linha:

Logo acima da linha:
```bash
local   all             all         peer
```

inserir a seguinte linha:
```bash
local   all              helios                         md5
```

A configuração acima corrige o seguinte erro:

```bash
Exception Type: 	OperationalError
Exception Value: 	
FATAL:  Peer authentication failed for user "helios"
```


>**Observação:** Com a configuração padrão do postgresql só é possível se conectar nele a partir da máquina em que ele está instalado. Caso você queira se conectar na base com um cliente como o pgAdmin, sem abrir a configuração para conexão a partir de outra máquina, basta utilizar um túnel ssh. Editar `~/.ssh/config` e inserir a entrada abaixo, substituindo os valores em letra maiúscula pelas configurações da sua instalação (e não esquecer que precisa haver uma conexão ssh aberta com o servidor do banco para que a configuração abaixo seja efetiva!):
>
>```bash
>Host NOMEDOHOST
>User NOMEDOUSER
>Hostname ENDERECODOHOST
>Port PORTASSH
>LocalForward PORTALOCAL 127.0.0.1:PORTAREMOTA
>```

Todas as instruções abaixo devem ser executadas com o usuário `helios` e não com o superusuário (root).

Baixe o código fonte desse repositório:
```bash
git clone https://github.com/shirlei/helios-server.git
```

Não é obrigatório, mas é uma boa prática, criar um ambiente virtual python para a disponibilização do Helios, pois isso permite separar as dependências do projeto e não interferir em outros sistemas na mesma máquina. 

Instale o `virtualenv` por meio do `pip`:

```bash
pip install virtualenv
```

Dentro do diretório onde o Helios foi baixado, execute o comando:

```bash
virtualenv venv
```

Isso criará um ambiente virtual python dentro do subdiretório chamado `venv`. Por fim, carregue o script `venv/bin/activate` para fazer uso do ambiente virtual: 

```bash
source venv/bin/activate
```

Com o ambiente virtual ativado, instale os pacotes que estão listados no arquivo `requirements.txt`:
```bash
pip install -r requirements.txt
```

> **ATENÇÃO:** Utilize o `requirements.txt` deste repositório para instalar o pacote `django-auth-ldap` e outros necessários para as personalizações que foram feitas no Helios. Lembrando também que apesar de se pretender manter este repositório atualizado com o do [Ben Adida](https://github.com/benadida/helios-server), não necessariamente vai ser simultâneo, então se você utilizar o dele, pode haver versões diferentes de pacotes.

Edite o arquivo `settings.py` e localize a seção databases. Adicione as informações para conexão no banco de dados, conforme o exemplo:

```bash
DATABASES = {
'default': {
'ENGINE': 'django.db.backends.postgresql_psycopg2',
'NAME': 'helios',
'USER': 'helios',
'HOST': 'localhost',
'PASSWORD': 'SENHADOHELIOS'
}}
```

Por fim, você precisará executar o script `reset.sh` (não faça como root) que fará a inicialização do esquema no banco de dados (criará as tabelas, etc.)
```bash
./reset.sh
```

> **Observação:** Se tiver algum problema ao executar o script acima, provavelmente vai ser relacionado à configuração do PostgreSQL e, nesse caso, o *Google é seu amigo.* Porém, o erro mais comum é que você tenha executado o script como root e o `postgres` acuse que não há um usuário root. Recomendo criar um usuário que não seja root (por exemplo, helios) e usar o mesmo nome para usuário do banco. Ou executar os comandos contidos no script com o usuário adequado do banco.

### Compilando arquivos com as traduções para português

A interface do Helios foi traduzida para o português e assim é necessário que compile os arquivos de tradução, caso queira usar a tradução que fizemos. Execute o seguinte comando a partir do diretório do Helios:
```bash
python manage.py compilemessages
```

Após a compilação, arquivos `.mo` devem ter sido gerados em `locale/pt_BR/LC_MESSAGES`

> **Observação:** Para alterar alguma tradução é possível utilizar o aplicativo [POEDIT](https://poedit.net), os mesmo editar diretamente os arquivos `django.po` e `djangojs.po` no editor de texto de sua preferência.

### Configuração dos módulos de autenticação

Você precisará habilitar em `settings.py` os módulos de autenticação que deseja. Por exemplo, poderia usar os módulos de autenticação do projeto original e permitir a autenticação de usuários por meio de contas Google, Facebook ou Twitter. 

Na seção abaixo apresentamos as configurações necessárias para permitir a autenticação de usuários de uma base LDAP. Se não tiver um servidor LDAP e só queira testar o Helios, então talvez possa ser interessante tentar com os outros módulos de autenticação citados acima.

#### Autenticação em uma base LDAP

Habilite o módulo LDAP em `settings.py`:

```bash
AUTH_ENABLED_AUTH_SYSTEMS = get_from_env('AUTH_ENABLED_AUTH_SYSTEMS', 'ldap').split(",")
```

A documentação da biblioteca utilizada pode ser encontrada em http://pythonhosted.org/django-auth-ldap/example.html. Ela não é muito completa, mas as configurações principais estão no `settings.py` e são: `AUTH_LDAP_SERVER_URI`, `AUTH_LDAP_BIND_PASSWORD`, e `AUTH_LDAP_USER_SEARCH`. 

As opções `AUTH_LDAP_BIND_DN` e `AUTH_LDAP_BIND_PASSWORD` deverão ter um valor configurado se o servidor LDAP exigir autenticação de usuário mesmo que seja para fazer consultas.


### Testando a instalação em ambiente de desenvolvimento

Ao executar o script `reset.sh`, você teve que criar um usuário de administração do django. Isso se deve ao fato de aplicação `admin` estar habilitada no arquivo `settings.py` (django.contrib.admin), pois iremos utilizá-la em algumas personalizações feitas para este *fork* do Helios.

Se tudo estiver correto até aqui, agora você poderá executar o servidor web para desenvolvimento que é provido pelo próprio django. Use esse servidor somente para verificar se a instalação foi feita com sucesso, porém não use-o caso queira colocar o Helios no ambiente de produção.

Execute o seguinte comando:

```bash
python manage.py runserver 0.0.0.0:8000
```

Abra um outro terminal para deixar o [celery](https://docs.celeryproject.org/en/stable/) em execução. Essa parte é importante, pois é celery quem vai gravar os votos, enviar emails, processar o arquivo de eleitores, etc.

```bash
python manage.py celeryd
```

Feito isso, você pode acessar a URL http://endereco-do-seu-servidor-helios e se autenticar com algum usuário presente em sua base LDAP (ou um usuário de algum outro sistema de autenticação que tenha habilitado para o Helios).

Esse usuário não conseguirá criar eleições ainda, mas esse passo é necessário para que seja criada uma entrada para esse usuário na base. No próximo passo, usaremos a aplicação `admin` do django para dar privilégio de gestor de eleição para esse usuário.

Acesse a URL http://endereco-do-seu-servidor-helios/admin e se autentique com o usuário e senha de administração (você fez isso quando executou o script `reset.sh`). 

Na página de administração são apresentados os *apps* habilitados. Localize a opção `Helios_Auth` e clique em *Users*. Na página seguinte, escolha o usuário que você deseja editar (basta clicar somente o login do mesmo). Na página de edição, marque a opção *Admin_p* e salve.

Pronto! O usuário em questão recebeu o papel de **gestor de eleição** e será capaz de criar e gerenciar eleições com o Helios.

> **Atenção**: só será possível dar o privilégio `admin_p` para usuários que se autenticaram previamente na aplicação Helios


## Preparando ambiente de produção

O servidor web usado na seção anterior é apenas para desenvolvimento e não deve ser usado em um ambiente de produção. 

É possível trabalhar com diversos servidores web, porém no caso em questão optou-se pelo [Apache](https://docs.djangoproject.com/en/1.8/topics/install/#install-apache-and-mod-wsgi).

### Configuração apache

Módulos a serem habilitados, para a configuração exemplo:
```bash
sudo a2enmod rewrite
sudo a2enmod ssl
```
Para configurar o `httpd.conf` ou equivalente, siga as instruções em [How to use Django with Apache and mod_wsgi](https://docs.djangoproject.com/en/1.8/howto/deployment/wsgi/modwsgi/).

A parte de servir os arquivos estáticos é a mais trabalhosa. Essa configuração é necessária porque no servidor de desenvolvimento o django serve esses arquivos, porém na produção, eles precisam ser configurados para serem servidos pelo servidor *web*.

Os arquivos estáticos não servidos pelo django são os "tradicionais":  css, javascript e imagens, por exemplo. Para coletar esses arquivos, é preciso executar o comando `collectstatic`, conforme descrito em [Collect static app](https://docs.djangoproject.com/en/1.8/ref/contrib/staticfiles//).

No caso do Helios em particular, há módulos sendo servidos estaticamente (total ou parcial): o `heliosbooth` e o `heliosverifier`, os quais também precisam ser configurados.

Como o enfoque deste repositório está no desenvolvimento de novas funcionalidades e especialmente na personalização do Helios para o uso por entidades brasileiras, optou-se por uma solução menos elegante para os arquivos estáticos, mas que simplifica muito: 
 - fazer um *link* simbólico dos arquivos desses módulos e  dos demais arquivos que precisam ser servidos estaticamente. E então configurar um *alias* para eles na configuração do apache, conforme os seguintes exemplos:

```bash
Alias /booth /`<path_to_site>`/sitestatic/booth

Alias /verifier /`<path_to_site>`/sitestatic/verifier
```

Além desses, todos os demais arquivos a serem servidos diretamente pelo apache, como os do módulo `admin` do django estão com links simbólicos no diretório `sitestatic`, que está sob controle do git. Ou seja, não é necessário rodar o comando `collectstatic`, apenas configurar o apache para apontar para o diretório `sitestatic` contido neste projeto, conforme exemplo de configuração acima.


>**Observações:**
>
>1. Neste repositório há um arquivo exemplo de configuração do Apache, o arquivo [helios.conf.exemplo](https://github.com/shirlei/helios-server/blob/master/helios.conf.exemplo). É um exemplo funcional para ambiente de homologação/dev com >Apache, mas é bastante similar à ambiente de produção, especialmente com relação aos alias necessários.
>
>2. Em algumas instalações mais recentes usando Apache tem havido relatos de problemas (internal server erros, com logs com registro de segmentation fault ou >outros), para o qual se identificou que atualizando a biblioteca pyscopg2 (para psycopg2-2.8.5) e instalando a libpq-dev, resolvia. Obrigada ao pessoal do IF >Sudeste MG por compartilhar a solução.

### Celery

Lembrando mais uma vez que o [celery](http://www.celeryproject.org/) precisa estar em execução, pois ele é o enfileirador de tarefas, como a tarefa de envio de emails e a tarefa de registro de votos.

Em produção é interessante rodar o celery com múltiplos processos, para acelerar por exemplo envio de emails.  Na prática, 5 processos em paralelo se mostrou suficiente. 

O *script* `check-services.sh` foi criado para verificar se o serviço celery está execução e contém o comando para executar o celery com 5 processos paralelos. Ele pode ser adicionado à crontab, como no exemplo abaixo, no qual ele executa de 10 em 10 minutos.

```bash
*/10 * * * *  /var/www/helios-server/check-services.sh >/dev/null 2>&1
```

Nesse mesmo *script*, também é verificado o [celery beat](http://docs.celeryproject.org/en/latest/userguide/periodic-tasks.html), agendador de tarefas periódicas, como limpar a tabela `celery_taskmeta`, que mantém o *log* das tarefas e pode crescer bastante.

>**Observação:**
>Gerenciar esses processos com o [supervisor](http://supervisord.org/introduction.html) é mais recomendado, em momento oportuno essa documentação será atualizada com exemplos.

No arquivo `settings.py` no presente repositório, colocou-se 60 dias como o prazo para apagar essas tarefas:

```bash
CELERYBEAT_SCHEDULER = 'djcelery.schedulers.DatabaseScheduler'

CELERY_TASK_RESULT_EXPIRES = 5184000 # 60 days
```

Após iniciar o celery beat, é possível ver uma tarefa periódica criada por meio da interface administrativa do django, sob Djecelery, periodic tasks. Se não desejar limpar da tabela dessa forma, basta não iniciar o celery beat.

## Configurações Gerais:

- Para o ambiente de produção, em `settings.py`, configurar `ALLOWED_HOSTS` para o seu domínio. Exemplo:
  ```bash
  # set a value for production environment, alongside with debug set to false
  ALLOWED_HOSTS = get_from_env('ALLOWED_HOSTS', 'endereco-do-seu-servidor-helios').split(",")
  ```
- Para que qualquer usuário que se logar no sistema possa receber automaticamente o papel de **gestor de eleição**, e por consequência, receber o privilégio para criar e gerir eleições, edite o arquivo `settings.py` e deixe como `False` a opção `HELIOS_ADMIN_ONLY`


## Personalizações feitas no Helios

### Listar eleições na página inicial do Helios

Outra personalização disponível, acessível por meio da aplicação de administração do django, é a opção de listar ou não uma eleição na página pública inicial do sistema. Se você quiser que uma eleição seja listada na página inicial do Helios, faça:
- Na página de administração do Django, localize a opção `Helios` e clique em *Elections*. 
- Na página seguinte, clique no nome da eleição que você gostaria que fosse listada na página pública e na tela de edição, marque a opção *Featured p* e salve.

### Autenticação federada via shibboleth

Para a utilização federada do Helios, diversas personalizações foram efetuadas tanto na página pública, quando na parte de gerenciamento de eleições. Essas personalizações estão hoje no ramo `helios_shibboleth` e somente no repositório https://github.com/shirlei/helios-server. 

#### Configuração da autenticação com o módulo apache shibboleth2

Além do módulo de autenticação LDAP, também foi desenvolvido um módulo de autenticação considerando o módulo shibboleth2 para o Apache. Nesse caso, o Helios funciona como um Provedor de Serviço (Service Provider - SP).

> Se o SP estiver na federação, então qualquer usuário autenticado em um IdP da federação será capaz de acessar o Helios. Agora se o SP não ficar na federação, então é possível estabelecer confiança mútua entre o SP e o IdP de sua instituição. Dessa forma, somente os usuários oriundos do IdP de sua instituição poderão acessar o SP Helios

Para utilizar essa funcionalidade, deve-se instalar o módulo apache shibb (funcionalidade testada com libapache2-mod-shib2) do servidor que vai servir o SP Helios e efetuar as configurações necessárias do shibboleth. Essas configurações incluem por exemplo o estabelecimento de confiança com o IdP, obtenção de metadados do IdP, envio de metadados do SP para o IdP, etc. Um bom ponto de partida, caso a instituição não costume configurar SPs shibboleth, é pesquisar por tutoriais que auxiliem na configuração de um SP.

Além disso, o módulo de autenticação shibboleth deve ser habilitado no arquivo `settings.py` e torná-lo padrão, para que a interface multi-instituição seja utilizada:

```bash
AUTH_ENABLED_AUTH_SYSTEMS = get_from_env('AUTH_ENABLED_AUTH_SYSTEMS', 'shibboleth').split(",")

AUTH_DEFAULT_AUTH_SYSTEM = get_from_env('AUTH_DEFAULT_AUTH_SYSTEM', 'shibboleth')
```

Deve-se também configurar os demais atributos em `settings.py`, na seção `#Shibboleth auth settings`.

> **Observação:** As configurações aqui indicadas supõe que o provedor de serviço (apache, módulo shibboleth e demais configurações) está configurado e funcional.


#### Habilitando instituições da federação para usarem o serviço Helios

Toda instituição a utilizar o Helios federado deve ser previamente cadastrada. Esse cadastro é feito na parte administrativa do Django. Acesse http://endereco-do-seu-servidor-helios/admin, procure por *HeliosInstitution* e clique em *Institutions* e então em *Adicionar Institution*. Forneça os dados necessários e clique em salvar.

Toda instituição deve ter pelo menos um usuário com o papel de **administrador da instituição**. Para adicionar esse papel a um usuário acesse o aplicativo *admin* do Django e:

1. Em *HeliosInstitution*, clique em *Institution user profiles* e depois em *Adicionar institution user profiles*
2. Se o usuário a ser cadastrado já se conectou alguma vez via federação, deve aparecer no campo *Helios user*. Se não, deixe em branco. 
3. No campo *django user*, é necessário adicionar um novo usuário. Clique no ícone + e informe no campo usuário o email do administrador e em permissões selecione *Institution Admin*. Clique em salvar. 
4. No campo *institution*, selecione a instituição previamente criada.
5. Em e-mail, informe o e-mail do administrador. Se desejar, informe a data de expiração desse usuário. Deixe o campo *active* desmarcado (será marcado quando o usuário se conectar no serviço pela primeira vez).

## Alguns lembretes finais cruciais para o ambiente de produção

- Em `settings.py` alterar de `True` para `False` o valor da constante `DEBUG`
- Alterar obrigatoriamente o valor do [SECRET_KEY](https://docs.djangoproject.com/en/dev/ref/settings/#std:setting-SECRET_KEY). Há ferramentas na web pra isso, como a disponível em [http://www.miniwebtool.com/django-secret-key-generator/](http://www.miniwebtool.com/django-secret-key-generator/)
- Conforme indicado no `settings.py`, não se deve alterar o valor da opção `SECURE_URL_HOST` após você já ter o sistema em produção, com eleições criadas (em andamento ou finalizadas), pois caso contrário a URL para depósito da cédula se tornará inválida.

