# 📊 Sistema de Solicitações — Análise de Dados

Formulário profissional para receber e gerenciar demandas do setor de Análise de Dados.

---

## ✅ O que este sistema faz

- **Formulário para o solicitante**: nome, setor, tipo de solicitação, objetivo, contexto, resultado esperado e frequência de entrega
- **Painel do administrador**: recebe as demandas, define prazo, vincula analista e atualiza o status (Aberta / Em execução / Concluída)
- **Exportação**: baixar todas as demandas em CSV (abre no Excel)

---

## 🚀 Passo a passo completo para publicar

### PASSO 1 — Criar conta no GitHub

1. Acesse [github.com](https://github.com)
2. Clique em **Sign up** (canto superior direito)
3. Preencha: e-mail, senha, nome de usuário
4. Confirme o e-mail que chegará na sua caixa de entrada
5. Pronto, conta criada!

---

### PASSO 2 — Criar o repositório no GitHub

1. Após fazer login no GitHub, clique no botão verde **"New"** (ou no **"+"** no canto superior direito → *New repository*)
2. Preencha:
   - **Repository name**: `demandas-analise-dados`
   - **Description** (opcional): `Sistema de solicitações para o setor de Análise de Dados`
   - Marque: ✅ **Public** (necessário para o Streamlit Cloud gratuito)
   - Marque: ✅ **Add a README file**
3. Clique em **Create repository**

---

### PASSO 3 — Fazer upload dos arquivos

Dentro do repositório que você acabou de criar:

1. Clique em **"Add file"** → **"Upload files"**
2. Arraste (ou selecione) os seguintes arquivos:
   - `app.py`
   - `requirements.txt`
   - `.gitignore`
3. Na área **"Commit changes"**, escreva uma mensagem como:
   `Adiciona sistema de solicitações`
4. Clique em **"Commit changes"**

> 💡 **Importante**: o arquivo `.gitignore` pode ficar invisível no seu computador pois começa com ponto. No Windows, para visualizá-lo: Painel de Controle → Opções de Pasta → Ver → marque "Mostrar arquivos ocultos".

---

### PASSO 4 — Criar conta no Streamlit Cloud

1. Acesse [share.streamlit.io](https://share.streamlit.io)
2. Clique em **"Sign up"**
3. Escolha **"Continue with GitHub"** — isso conecta sua conta do GitHub automaticamente
4. Autorize o Streamlit a acessar seus repositórios

---

### PASSO 5 — Publicar o app

1. No Streamlit Cloud, clique em **"New app"**
2. Preencha:
   - **Repository**: selecione `demandas-analise-dados`
   - **Branch**: `main`
   - **Main file path**: `app.py`
3. Clique em **"Deploy!"**
4. Aguarde cerca de 1 a 2 minutos enquanto o Streamlit instala tudo
5. Seu app estará disponível em um endereço como:
   `https://seu-usuario-demandas-analise-dados.streamlit.app`

---

### PASSO 6 — Compartilhar o link

Copie o link gerado e envie para as pessoas que precisam preencher o formulário!

---

## ⚠️ Aviso importante sobre os dados

Por padrão, as demandas são salvas no arquivo `demandas.json` **dentro do servidor do Streamlit Cloud**.

**Isso significa que:**
- ✅ Funciona perfeitamente para testes e uso inicial
- ⚠️ Os dados podem ser apagados quando o app for atualizado ou reiniciado

**Para não perder dados em produção**, conecte a um banco de dados. A opção mais fácil é usar o **Google Sheets** (veja a seção abaixo).

---

## 📊 Integração com Google Sheets (recomendado para produção)

Se quiser que os dados fiquem salvos permanentemente no Google Sheets, siga estes passos extras:

### 1. Crie uma planilha no Google Sheets
   - Acesse [sheets.google.com](https://sheets.google.com)
   - Crie uma nova planilha chamada `Demandas Análise de Dados`
   - Na primeira linha, coloque os cabeçalhos:
     `id | data | nome | setor | tipo | objetivo | contexto | resultado | frequencia | status | analista | prazo`

### 2. Crie as credenciais do Google
   - Acesse [console.cloud.google.com](https://console.cloud.google.com)
   - Crie um projeto novo
   - Ative a API **Google Sheets** e a API **Google Drive**
   - Crie uma **Conta de Serviço** e baixe o arquivo JSON de credenciais

### 3. Configure os segredos no Streamlit
   - No Streamlit Cloud, vá em **Settings → Secrets**
   - Cole o conteúdo do JSON de credenciais no formato:
   ```toml
   [gcp_service_account]
   type = "service_account"
   project_id = "seu-projeto"
   ...
   ```

> Para um tutorial detalhado, pesquise: **"Streamlit Google Sheets tutorial"** no YouTube.

---

## 📁 Estrutura dos arquivos

```
demandas-analise-dados/
├── app.py            ← código principal do sistema
├── requirements.txt  ← bibliotecas necessárias
├── .gitignore        ← arquivos a ignorar no GitHub
└── README.md         ← este guia
```

---

## 🆘 Problemas comuns

| Problema | Solução |
|----------|---------|
| App não abre | Verifique se o `requirements.txt` está correto |
| Erro ao salvar demanda | Verifique se o `app.py` está na raiz do repositório |
| App fica reiniciando | Normal no plano gratuito — os dados do JSON podem ser perdidos |
| Não encontra o arquivo `.gitignore` | No Windows, ative a exibição de arquivos ocultos |

---

*Desenvolvido para o setor de Análise de Dados.*
