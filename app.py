from flask import Flask, render_template, request, redirect, url_for, session, send_file
import pandas as pd
import os
import xmltodict
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time
import re

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Substitua por uma chave secreta segura


class CentralFrete:
    def __init__(self, headless=True):
        self.chrome_options = Options()
        if headless:
            self.chrome_options.add_argument("--headless")
        self.chrome_options.add_argument("--disable-gpu")
        self.chrome_options.add_argument("--no-sandbox")
        self.chrome_options.add_argument("--disable-dev-shm-usage")
        self.chrome_options.add_argument("--window-size=1920x1080")
        self.navegador = None

    def abrir_navegador(self):
        self.navegador = webdriver.Chrome(options=self.chrome_options)

    def importar_alto_giro(self, atlas_file, lote_file):
        try:
            atlas = pd.read_html(atlas_file)[0]
            atlas["SERIAL"] = atlas["Série / Ender. Princ."].str[-12:]
            atlas = atlas.rename(
                columns={
                    "Material SAP": "CÓDIGO",
                    "Local": "LOCAL TERMINAL",
                    "Estado": "ESTADO TERMINAL",
                }
            )
            atlas = atlas[["CÓDIGO", "SERIAL", "LOCAL TERMINAL", "ESTADO TERMINAL"]]

            atlas["STATUS PARA DEVOLUÇÃO"] = "OK PARA DEVOLUÇÃO"
            atlas["FORMULA TECNICOS"] = "SUSPEITO/EMPREITEIRA"
            atlas["STATUS DEVOLUÇÃO"] = "OK PARA DEVOLUÇÃO"

            lote = pd.read_excel(lote_file)
            atlas = pd.merge(atlas, lote, on="SERIAL", how="left")
            atlas = atlas.sort_values(by="CX")

            output_file = "PACKLIST TERM ALTO GIRO.xlsx"
            atlas.to_excel(output_file, index=False)
            return output_file
        except Exception as e:
            return str(e)

    def importar_baixo_giro(self, atlas_file, lote_file):
        try:
            atlas = pd.read_html(atlas_file)[0]
            atlas["SERIAL"] = atlas["Série / Ender. Princ."].str[-12:]
            atlas = atlas.rename(
                columns={
                    "Material SAP": "CÓDIGO",
                    "Local": "LOCAL TERMINAL",
                    "Estado": "ESTADO TERMINAL",
                }
            )
            atlas = atlas[["CÓDIGO", "SERIAL", "LOCAL TERMINAL", "ESTADO TERMINAL"]]

            atlas["STATUS PARA DEVOLUÇÃO"] = "OK PARA DEVOLUÇÃO"
            atlas["FORMULA TECNICOS"] = "SUSPEITO/EMPREITEIRA"
            atlas["STATUS DEVOLUÇÃO"] = "OK PARA DEVOLUÇÃO"

            lote = pd.read_excel(lote_file)
            atlas = pd.merge(atlas, lote, on="SERIAL", how="left")
            atlas = atlas.sort_values(by="CX")

            output_file = "PACKLIST TERM BAIXO GIRO.xlsx"
            atlas.to_excel(output_file, index=False)
            return output_file
        except Exception as e:
            return str(e)

    def juntar_packlist(self, alto_giro_file, baixo_giro_file):
        try:
            baixo_giro = pd.read_excel(baixo_giro_file)
            alto_giro = pd.read_excel(alto_giro_file)
            atlas_completo = pd.concat([baixo_giro, alto_giro])
            output_file = "PACKLIST TERM JUNTAS.xlsx"
            atlas_completo.to_excel(output_file, index=False)
            return output_file
        except Exception as e:
            return str(e)

    def packlist_acessorios(self, xml_file):
        try:
            with open(xml_file, "rb") as arquivo:
                documento = xmltodict.parse(arquivo)

            packlist_acessorios = pd.DataFrame()

            lista = documento["nfeProc"]["NFe"]["infNFe"]["det"]
            for item in lista:
                xml_data = item["prod"]
                df = pd.DataFrame([xml_data])
                packlist_acessorios = pd.concat(
                    [packlist_acessorios, df], ignore_index=True
                )

            packlist_acessorios = packlist_acessorios.rename(
                columns={"xProd": "LOCAL TERMINAL", "cProd": "CÓDIGO", "qCom": "SERIAL"}
            )
            packlist_acessorios = packlist_acessorios[
                ["CÓDIGO", "SERIAL", "LOCAL TERMINAL"]
            ]
            packlist_acessorios["ESTADO TERMINAL"] = "WORLD TELECOMUNICACOES"
            packlist_acessorios["STATUS PARA DEVOLUÇÃO"] = "OK PARA DEVOLUÇÃO"
            packlist_acessorios["FORMULA TECNICOS"] = "SUSPEITO/EMPREITEIRA"
            packlist_acessorios["STATUS DEVOLUÇÃO"] = "OK PARA DEVOLUÇÃO"
            packlist_acessorios["CX"] = "1"
            packlist_acessorios["SERIAL"] = packlist_acessorios["SERIAL"].apply(
                lambda x: int(float(x))
            )

            output_file = "PACKLIST ACESS.xlsx"
            packlist_acessorios.to_excel(output_file, index=False)
            return output_file
        except Exception as e:
            return str(e)

    def modelos_equipamentos(self, atlas_file, familia_equipamentos_file):
        try:
            modelos = pd.read_excel(familia_equipamentos_file)
            atlas = pd.read_excel(atlas_file)
            resumo = pd.merge(atlas, modelos, on="CÓDIGO", how="left")

            resumo["TÉCNOLOGIA"] = resumo["TÉCNOLOGIA"].fillna("Não encontrado")
            resumo["TIPO"] = resumo["TIPO"].fillna("Não encontrado")

            tecnologia = resumo.groupby(by="TÉCNOLOGIA").count()[["STATUS DEVOLUÇÃO"]]
            tecnologia.reset_index(inplace=True)
            tecnologia_file = "tecnologia.xlsx"
            tecnologia.to_excel(tecnologia_file, index=False)

            tipo = resumo.groupby(by="TIPO").count()[["STATUS DEVOLUÇÃO"]]
            tipo.reset_index(inplace=True)
            tipo_file = "tipo.xlsx"
            tipo.to_excel(tipo_file, index=False)

            return tecnologia_file, tipo_file
        except Exception as e:
            return str(e), None

    def lancar_material_no_central(
        self, cidade, valor_nota, quantidade_cx, upload_file, familia_equipamentos_file
    ):
        tecnologia_file, tipo_file = self.modelos_equipamentos(
            upload_file, familia_equipamentos_file
        )

        if not tecnologia_file or not tipo_file:
            return f"Erro ao gerar arquivos: {tecnologia_file}"

        self.abrir_navegador()
        atlas_completo = pd.read_excel(upload_file)
        self.navegador.get("https://terceiros.etms.com.br/")
        time.sleep(1)
        self.navegador.find_element(By.ID, "txtUsuario").send_keys(
            "raphael.silva@worldsistema.com.br"
        )
        time.sleep(1)
        self.navegador.find_element(By.ID, "txtSenha").send_keys("world2025")
        time.sleep(1)
        self.navegador.find_element(By.ID, "btLogon").click()
        time.sleep(1)
        self.navegador.get(
            "https://terceiros.etms.com.br/Cadastros/SOLICITACAO_COLETA.aspx"
        )
        time.sleep(1)
        self.navegador.find_element(By.ID, "ctl00_toolbar___BtNovo").click()
        time.sleep(0.5)
        self.navegador.find_element(
            By.ID, "ctl00_MainContent_btnNovaSolicitacao"
        ).click()
        time.sleep(0.5)

        def ver_cidade(cidade):
            if cidade == "GOIANIA":
                i = 3
            elif cidade == "BRASILIA":
                i = 1
            elif cidade == "CAMPO GRANDE":
                i = 2
            elif cidade == "ANAPOLIS":
                i = 4
            return i

        i = ver_cidade(cidade)
        self.navegador.find_element(
            By.XPATH, f'//*[@id="ctl00_MainContent_cmbParceiro"]/option[{i}]'
        ).click()
        time.sleep(2)
        self.navegador.find_element(By.ID, "ctl00_MainContent_txtCNPJ").send_keys(
            "66.970.229/0406-22"
        )
        time.sleep(1)
        self.navegador.find_element(By.ID, "ctl00_MainContent_btnConfirmarCNPJ").click()
        time.sleep(1)
        self.navegador.find_element(
            By.ID, "ctl00_MainContent_cmUnidadeEmpresa"
        ).send_keys("NXT WH REVENDA (N690)")
        time.sleep(1)
        self.navegador.find_element(By.ID, "ctl00_MainContent_txtVolume").send_keys(
            quantidade_cx
        )
        time.sleep(1)
        self.navegador.find_element(By.ID, "txtAltura").send_keys("0,35")
        time.sleep(1)
        self.navegador.find_element(By.ID, "ctl00_MainContent_txtLargura").send_keys(
            "0,29"
        )
        time.sleep(1)
        self.navegador.find_element(
            By.ID, "ctl00_MainContent_txtComprimento"
        ).send_keys("0,38")
        time.sleep(1)
        self.navegador.find_element(
            By.XPATH, '//*[@id="ctl00_MainContent_cmbSitMaterial"]/option[4]'
        ).click()
        time.sleep(1)
        self.navegador.find_element(By.ID, "ctl00_MainContent_btnAddCubagem").click()
        time.sleep(5)
        caixa = quantidade_cx
        peso = int(caixa) * 10
        self.navegador.find_element(By.ID, "txtPeso").send_keys(peso)
        time.sleep(1)
        self.navegador.find_element(By.ID, "ctl00_MainContent_txtValNF").send_keys(
            valor_nota
        )
        time.sleep(1)
        self.navegador.find_element(
            By.ID, "ctl00_MainContent_chkTransporteProprio"
        ).click()
        time.sleep(1)
        self.navegador.find_element(By.ID, "ctl00_MainContent_btnProxP1").click()

        tecnologia = pd.read_excel(tecnologia_file)
        teste = tecnologia.loc[tecnologia["STATUS DEVOLUÇÃO"] == "Não encontrado"]
        teste = len(teste)
        if teste < 1:

            time.sleep(1)
            for linha in tecnologia.index:
                tecno = tecnologia.loc[linha, "TÉCNOLOGIA"]
                quantidade = tecnologia.loc[linha, "STATUS DEVOLUÇÃO"]
                self.navegador.find_element(
                    By.ID, "ctl00_MainContent_cmbReceptores"
                ).send_keys(tecno)
                time.sleep(0.5)
                self.navegador.find_element(
                    By.ID, "ctl00_MainContent_TxtQtdReceptores"
                ).send_keys(str(quantidade))
                time.sleep(0.5)
                self.navegador.find_element(
                    By.ID, "ctl00_MainContent_BtAdicionar"
                ).click()
                time.sleep(3)

            self.navegador.find_element(By.ID, "ctl00_MainContent_btnProxP2").click()
            tipo = pd.read_excel(tipo_file)
            for linha in tipo.index:
                tecno = tipo.loc[linha, "TIPO"]
                quantidade = tipo.loc[linha, "STATUS DEVOLUÇÃO"]
                self.navegador.find_element(
                    By.ID, "ctl00_MainContent_cmbTipoDMT"
                ).send_keys(tecno)
                time.sleep(0.5)
                self.navegador.find_element(
                    By.ID, "ctl00_MainContent_txtNumDMT"
                ).send_keys(str(quantidade))
                time.sleep(0.5)
                self.navegador.find_element(
                    By.ID, "ctl00_MainContent_btnAdicionarDMT"
                ).click()
                time.sleep(3)
            time.sleep(1)
            self.navegador.find_element(By.ID, "ctl00_MainContent_btnProxP3").click()
            time.sleep(2)

            upload_file_abs = os.path.abspath(upload_file)
            if not os.path.exists(upload_file_abs):
                raise FileNotFoundError(f"Arquivo não encontrado: {upload_file_abs}")

            file_input = self.navegador.find_element(
                By.CSS_SELECTOR, "input[type='file']"
            )
            file_input.send_keys(upload_file_abs)
            time.sleep(1)
            self.navegador.find_element(By.ID, "ctl00_MainContent_btnSeriais").click()
            time.sleep(1)
            self.navegador.find_element(
                By.ID, "ctl00_MainContent_btnProxSeriais"
            ).click()
            time.sleep(1)
            self.navegador.find_element(
                By.ID, "ctl00_MainContent_btnGravarSolicitacao"
            ).click()
            time.sleep(2)
            solict = self.navegador.find_elements(By.ID, "tableLista")
            for i in solict:
                n = i.text
            match = re.search(r"\n\s*(\d{6})\s", n)

            if match:
                solicitacao = match.group(1)

            return f"Numero da solicitação: {solicitacao} Concluído: SO FALTA CONFIRMAR O PACKLIST E INCLUIR O XML"
        else:
            return "Tem tecnologia não localizada. Tem que cadastrar tecnologia."

    def lancar_acessorios_no_central(
        self, cidade, valor_nota, quantidade_cx, upload_file
    ):
        self.abrir_navegador()
        atlas_completo = pd.read_excel(upload_file)
        self.navegador.get("https://terceiros.etms.com.br/")
        time.sleep(1)
        self.navegador.find_element(By.ID, "txtUsuario").send_keys(
            "raphael.silva@worldsistema.com.br"
        )
        time.sleep(1)
        self.navegador.find_element(By.ID, "txtSenha").send_keys("world2024")
        time.sleep(1)
        self.navegador.find_element(By.ID, "btLogon").click()
        time.sleep(1)
        self.navegador.get(
            "https://terceiros.etms.com.br/Cadastros/SOLICITACAO_COLETA.aspx"
        )
        time.sleep(1)
        self.navegador.find_element(By.ID, "ctl00_toolbar___BtNovo").click()
        time.sleep(0.5)
        self.navegador.find_element(
            By.ID, "ctl00_MainContent_btnNovaSolicitacao"
        ).click()
        time.sleep(0.5)

        def ver_cidade(cidade):
            if cidade == "GOIANIA":
                i = 3
            elif cidade == "BRASILIA":
                i = 1
            elif cidade == "CAMPO GRANDE":
                i = 2
            elif cidade == "ANAPOLIS":
                i = 4
            return i

        i = ver_cidade(cidade)
        self.navegador.find_element(
            By.XPATH, f'//*[@id="ctl00_MainContent_cmbParceiro"]/option[{i}]'
        ).click()
        time.sleep(2)
        self.navegador.find_element(By.ID, "ctl00_MainContent_txtCNPJ").send_keys(
            "66.970.229/0406-22"
        )
        time.sleep(1)
        self.navegador.find_element(By.ID, "ctl00_MainContent_btnConfirmarCNPJ").click()
        time.sleep(1)
        self.navegador.find_element(
            By.ID, "ctl00_MainContent_cmUnidadeEmpresa"
        ).send_keys("NXT WH REVENDA (N690)")
        time.sleep(1)
        self.navegador.find_element(By.ID, "ctl00_MainContent_txtVolume").send_keys(
            quantidade_cx
        )
        time.sleep(1)
        self.navegador.find_element(By.ID, "txtAltura").send_keys("0,35")
        time.sleep(1)
        self.navegador.find_element(By.ID, "ctl00_MainContent_txtLargura").send_keys(
            "0,29"
        )
        time.sleep(1)
        self.navegador.find_element(
            By.ID, "ctl00_MainContent_txtComprimento"
        ).send_keys("0,38")
        time.sleep(1)
        self.navegador.find_element(
            By.XPATH, '//*[@id="ctl00_MainContent_cmbSitMaterial"]/option[4]'
        ).click()
        time.sleep(1)
        self.navegador.find_element(By.ID, "ctl00_MainContent_btnAddCubagem").click()
        time.sleep(5)
        caixa = quantidade_cx
        peso = int(caixa) * 10
        self.navegador.find_element(By.ID, "txtPeso").send_keys(peso)
        time.sleep(1)
        self.navegador.find_element(By.ID, "ctl00_MainContent_txtValNF").send_keys(
            valor_nota
        )
        time.sleep(1)
        self.navegador.find_element(
            By.ID, "ctl00_MainContent_chkTransporteProprio"
        ).click()
        time.sleep(1)
        self.navegador.find_element(By.ID, "ctl00_MainContent_btnProxP1").click()

        fonte = atlas_completo.loc[
            atlas_completo["LOCAL TERMINAL"].str.contains("ONTE")
        ]["SERIAL"].sum()
        controle = atlas_completo.loc[
            atlas_completo["LOCAL TERMINAL"].str.contains("REMO")
        ]["SERIAL"].sum()
        cabo = atlas_completo.loc[
            atlas_completo["LOCAL TERMINAL"].str.contains("CABO")
        ]["SERIAL"].sum()
        mini = atlas_completo.loc[
            atlas_completo["LOCAL TERMINAL"].str.contains("MINI")
        ]["SERIAL"].sum()
        time.sleep(1)

        self.navegador.find_element(By.ID, "ctl00_MainContent_cmbReceptores").send_keys(
            "FONTES"
        )
        time.sleep(0.5)
        self.navegador.find_element(
            By.ID, "ctl00_MainContent_TxtQtdReceptores"
        ).send_keys(str(fonte))
        time.sleep(0.5)
        self.navegador.find_element(By.ID, "ctl00_MainContent_BtAdicionar").click()
        time.sleep(3)

        self.navegador.find_element(By.ID, "ctl00_MainContent_cmbReceptores").send_keys(
            "CONTROLE REMOTO"
        )
        time.sleep(0.5)
        self.navegador.find_element(
            By.ID, "ctl00_MainContent_TxtQtdReceptores"
        ).send_keys(str(controle))
        time.sleep(0.5)
        self.navegador.find_element(By.ID, "ctl00_MainContent_BtAdicionar").click()
        time.sleep(3)

        self.navegador.find_element(By.ID, "ctl00_MainContent_cmbReceptores").send_keys(
            "CABOS"
        )
        time.sleep(0.5)
        self.navegador.find_element(
            By.ID, "ctl00_MainContent_TxtQtdReceptores"
        ).send_keys(str(cabo))
        time.sleep(0.5)
        self.navegador.find_element(By.ID, "ctl00_MainContent_BtAdicionar").click()
        time.sleep(3)

        self.navegador.find_element(By.ID, "ctl00_MainContent_cmbReceptores").send_keys(
            "MINI ISOLADOR"
        )
        time.sleep(0.5)
        self.navegador.find_element(
            By.ID, "ctl00_MainContent_TxtQtdReceptores"
        ).send_keys(str(mini))
        time.sleep(0.5)
        self.navegador.find_element(By.ID, "ctl00_MainContent_BtAdicionar").click()
        time.sleep(3)

        self.navegador.find_element(By.ID, "ctl00_MainContent_btnProxP2").click()
        quantidade = atlas_completo["SERIAL"].sum()
        self.navegador.find_element(By.ID, "ctl00_MainContent_cmbTipoDMT").send_keys(
            "Acessorios"
        )
        time.sleep(0.5)
        self.navegador.find_element(By.ID, "ctl00_MainContent_txtNumDMT").send_keys(
            str(quantidade)
        )
        time.sleep(0.5)
        self.navegador.find_element(By.ID, "ctl00_MainContent_btnAdicionarDMT").click()
        time.sleep(3)

        time.sleep(1)
        self.navegador.find_element(By.ID, "ctl00_MainContent_btnProxP3").click()
        time.sleep(2)

        upload_file_abs = os.path.abspath(upload_file)
        if not os.path.exists(upload_file_abs):
            raise FileNotFoundError(f"Arquivo não encontrado: {upload_file_abs}")

        file_input = self.navegador.find_element(By.CSS_SELECTOR, "input[type='file']")
        file_input.send_keys(upload_file_abs)
        time.sleep(1)
        self.navegador.find_element(By.ID, "ctl00_MainContent_btnSeriais").click()
        time.sleep(1)
        self.navegador.find_element(By.ID, "ctl00_MainContent_btnProxSeriais").click()
        time.sleep(1)
        self.navegador.find_element(
            By.ID, "ctl00_MainContent_btnGravarSolicitacao"
        ).click()
        time.sleep(2)
        solict = self.navegador.find_elements(By.ID, "tableLista")
        for i in solict:
            n = i.text
        match = re.search(r"\n\s*(\d{6})\s", n)

        if match:
            solicitacao = match.group(1)
        return f"Numero da solicitação: {solicitacao} Concluído: SO FALTA CONFIRMAR O PACKLIST E INCLUIR O XML"


# Rota de login


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if (
            username == "veld" and password == "veld1234"
        ):  # Substitua com credenciais seguras
            session["logged_in"] = True
            return redirect(url_for("index"))
        else:
            return "Credenciais inválidas, tente novamente."

    return render_template("login.html")


# Verificar se o usuário está logado antes de acessar as rotas protegidas
from functools import wraps


def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if "logged_in" in session:
            return f(*args, **kwargs)
        else:
            return redirect(url_for("login"))

    return wrap


@app.route("/")
@login_required
def index():
    return render_template("index.html")


@app.route("/importar_alto_giro", methods=["POST"])
def importar_alto_giro():
    atlas_file = request.files["atlas_file"]
    lote_file = request.files["lote_file"]

    atlas_path = os.path.join(os.getcwd(), atlas_file.filename)
    lote_path = os.path.join(os.getcwd(), lote_file.filename)

    atlas_file.save(atlas_path)
    lote_file.save(lote_path)

    central_frete = CentralFrete()
    output_file = central_frete.importar_alto_giro(atlas_path, lote_path)

    if not output_file.endswith(".xlsx"):
        return f"Erro: {output_file}", 500

    return send_file(output_file, as_attachment=True)


@app.route("/importar_baixo_giro", methods=["POST"])
def importar_baixo_giro():
    atlas_file = request.files["atlas_file"]
    lote_file = request.files["lote_file"]

    atlas_path = os.path.join(os.getcwd(), atlas_file.filename)
    lote_path = os.path.join(os.getcwd(), lote_file.filename)

    atlas_file.save(atlas_path)
    lote_file.save(lote_path)

    central_frete = CentralFrete()
    output_file = central_frete.importar_baixo_giro(atlas_path, lote_path)

    if not output_file.endswith(".xlsx"):
        return f"Erro: {output_file}", 500

    return send_file(output_file, as_attachment=True)


@app.route("/juntar_packlist", methods=["POST"])
def juntar_packlist():
    # Receber os arquivos enviados no formulário
    alto_giro_file = request.files["alto_giro_file"]
    baixo_giro_file = request.files["baixo_giro_file"]

    # Definir os caminhos para salvar os arquivos no servidor temporariamente
    alto_giro_path = os.path.join(os.getcwd(), alto_giro_file.filename)
    baixo_giro_path = os.path.join(os.getcwd(), baixo_giro_file.filename)

    # Salvar os arquivos no servidor
    alto_giro_file.save(alto_giro_path)
    baixo_giro_file.save(baixo_giro_path)

    # Instanciar a classe CentralFrete
    central_frete = CentralFrete()

    # Chamar o método juntar_packlist com os caminhos dos arquivos como parâmetros
    output_file = central_frete.juntar_packlist(alto_giro_path, baixo_giro_path)

    # Verificar se o arquivo foi gerado corretamente
    if not output_file.endswith(".xlsx"):
        # Remover os arquivos temporários em caso de erro
        os.remove(alto_giro_path)
        os.remove(baixo_giro_path)
        return f"Erro: {output_file}", 500

    # Remover os arquivos temporários após o processamento
    os.remove(alto_giro_path)
    os.remove(baixo_giro_path)

    # Enviar o arquivo gerado para download
    return send_file(output_file, as_attachment=True)


@app.route("/packlist_acessorios", methods=["POST"])
def packlist_acessorios():
    xml_file = request.files["xml_file"]

    xml_path = os.path.join(os.getcwd(), xml_file.filename)
    xml_file.save(xml_path)

    central_frete = CentralFrete()
    output_file = central_frete.packlist_acessorios(xml_path)

    if not output_file.endswith(".xlsx"):
        return f"Erro: {output_file}", 500

    return send_file(output_file, as_attachment=True)


@app.route("/lancar_material_no_central", methods=["POST"])
def lancar_material_no_central():
    cidade = request.form["cidade"]
    valor_nota = request.form["valor_nota"]
    quantidade_cx = request.form["quantidade_cx"]
    upload_file = request.files["upload_file"]
    familia_equipamentos_file = request.files["familia_equipamentos"]

    upload_path = os.path.join(os.getcwd(), upload_file.filename)
    familia_equipamentos_path = os.path.join(
        os.getcwd(), familia_equipamentos_file.filename
    )

    upload_file.save(upload_path)
    familia_equipamentos_file.save(familia_equipamentos_path)

    central_frete = CentralFrete()
    result = central_frete.lancar_material_no_central(
        cidade, valor_nota, quantidade_cx, upload_path, familia_equipamentos_path
    )

    return result


@app.route("/lancar_acessorios_no_central", methods=["POST"])
def lancar_acessorios_no_central():
    cidade = request.form["cidade"]
    valor_nota = request.form["valor_nota"]
    quantidade_cx = request.form["quantidade_cx"]
    upload_file = request.files["upload_file"]

    upload_path = os.path.join(os.getcwd(), upload_file.filename)
    upload_file.save(upload_path)

    central_frete = CentralFrete()
    result = central_frete.lancar_acessorios_no_central(
        cidade, valor_nota, quantidade_cx, upload_path
    )

    return result


if __name__ == "__main__":
    app.run(debug=True)
