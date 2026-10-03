import unittest
import zipfile
from datetime import date
from pathlib import Path

import pandas as pd

from eleitoral.analise import comparar_disputas, cruzar_deputados, resumo_por_partido
from eleitoral.regras import (
    detectar_encoding,
    eh_apto,
    eh_eleito,
    eh_publicidade,
    escolher_csvs,
    formatar_reais,
    parse_valor,
)
from eleitoral.tse import candidatos_do_arquivo, montar_gastos, _acumular_despesas


def _csv_candidatos(linhas: list[str]) -> str:
    cabecalho = (
        "ANO_ELEICAO;CD_TIPO_ELEICAO;NM_TIPO_ELEICAO;NR_TURNO;SG_UF;CD_CARGO;DS_CARGO;"
        "SQ_CANDIDATO;NR_CANDIDATO;NM_CANDIDATO;NM_URNA_CANDIDATO;NR_CPF_CANDIDATO;"
        "NR_TITULO_ELEITORAL_CANDIDATO;DS_SITUACAO_CANDIDATURA;SG_PARTIDO;NM_PARTIDO;"
        "DS_SIT_TOT_TURNO;DT_NASCIMENTO;SG_FEDERACAO"
    )
    return cabecalho + "\n" + "\n".join(linhas) + "\n"


class RegrasTeste(unittest.TestCase):
    def test_valor_brasileiro(self):
        self.assertEqual(parse_valor("1.234,56"), 1234.56)
        self.assertEqual(parse_valor("1000,50"), 1000.50)
        self.assertEqual(parse_valor("10"), 10.0)
        self.assertEqual(formatar_reais(1234.5), "R$ 1.234,50")

    def test_publicidade_e_eleicao(self):
        self.assertTrue(eh_publicidade("Publicidade por materiais impressos"))
        self.assertTrue(eh_publicidade("Despesa com Impulsionamento de conteúdos"))
        self.assertTrue(eh_publicidade("Criação e inclusão de páginas na internet"))
        self.assertFalse(eh_publicidade("Combustíveis e lubrificantes"))
        self.assertTrue(eh_eleito("ELEITO POR QP"))
        self.assertTrue(eh_eleito("ELEITO POR MÉDIA"))
        self.assertFalse(eh_eleito("NÃO ELEITO"))
        self.assertFalse(eh_eleito("SUPLENTE"))
        self.assertTrue(eh_apto("#NE"))
        self.assertTrue(eh_apto("APTO"))
        self.assertFalse(eh_apto("INAPTO"))

    def test_prioriza_arquivo_brasil(self):
        nomes = [
            "consulta_cand_2022_AC.csv",
            "consulta_cand_2022_BRASIL.csv",
            "leia-me.pdf",
        ]
        self.assertEqual(escolher_csvs(nomes, "consulta_cand"), ["consulta_cand_2022_BRASIL.csv"])

    def test_prioriza_arquivo_do_estado(self):
        nomes = [
            "consulta_cand_2022_AC.csv",
            "consulta_cand_2022_AM.csv",
            "consulta_cand_2022_BRASIL.csv",
        ]
        self.assertEqual(escolher_csvs(nomes, "consulta_cand", uf="am"), ["consulta_cand_2022_AM.csv"])

    def test_detecta_utf8_lido_como_latin1(self):
        amostra = "João".encode("utf-8")
        self.assertEqual(detectar_encoding(amostra), "utf-8")
        self.assertEqual(detectar_encoding("João".encode("latin-1")), "latin-1")


class ArquivosTeste(unittest.TestCase):
    def test_candidatos_filtram_cargo_situacao_e_arquivo_nacional(self):
        brasil = _csv_candidatos(
            [
                "2022;2;Eleição Ordinária;1;SP;6;Deputado Federal;10;1234;João da Silva;JOÃO;12345678901;111;APTO;PT;Partido dos Trabalhadores;ELEITO POR QP;01/02/1980;PT-PCdoB-PV",
                "2022;2;Eleição Ordinária;1;RJ;6;Deputado Federal;11;2222;Maria Souza;MARIA;10987654321;222;INAPTO;PL;Partido Liberal;#NULO#;03/04/1975;",
                "2022;2;Eleição Ordinária;1;MG;7;Deputado Estadual;12;3333;Pedro Lima;PEDRO;11122233344;333;APTO;MDB;Movimento Democrático Brasileiro;#NULO#;05/06/1990;",
                "2022;1;Eleição Suplementar;1;BA;6;Deputado Federal;13;4444;Ana Costa;ANA;55566677788;444;APTO;PSB;Partido Socialista Brasileiro;#NULO#;07/08/1988;",
            ]
        )
        uf = _csv_candidatos(
            [
                "2022;2;Eleição Ordinária;1;AC;6;Deputado Federal;99;9999;Fantasma;FANTASMA;00011122233;999;APTO;PP;Progressistas;#NULO#;09/09/1970;",
            ]
        )
        destino = Path(self.id().replace(".", "_") + ".zip")
        try:
            with zipfile.ZipFile(destino, "w") as arquivo:
                arquivo.writestr("consulta_cand_2022_BRASIL.csv", brasil.encode("latin-1"))
                arquivo.writestr("consulta_cand_2022_AC.csv", uf.encode("latin-1"))
            quadro = candidatos_do_arquivo(destino, 2022)
        finally:
            destino.unlink(missing_ok=True)

        self.assertEqual(list(quadro["nome_urna"]), ["JOÃO"])
        self.assertEqual(quadro.loc[0, "partido"], "PT")
        self.assertNotIn("FANTASMA", set(quadro["nome_urna"]))

    def test_publicidade_respeita_o_corte_de_28_de_setembro(self):
        csv = (
            "DT_GERACAO;SQ_CANDIDATO;CD_CARGO;DS_ORIGEM_DESPESA;DT_DESPESA;VR_DESPESA_CONTRATADA\n"
            "28/09/2026;10;6;Publicidade por materiais impressos;10/09/2026;1.000,50\n"
            "28/09/2026;10;6;Publicidade por materiais impressos;01/10/2026;999,00\n"
            "28/09/2026;10;6;Combustíveis e lubrificantes;05/09/2026;50,00\n"
            "28/09/2026;20;6;Despesa com Impulsionamento de conteúdos;28/09/2026;10,00\n"
            "28/09/2026;20;6;Despesa com Impulsionamento de conteúdos;29/09/2026;10,00\n"
            "28/09/2026;10;6;Publicidade por adesivos;;15,00\n"
            "28/09/2026;30;6;Publicidade por jornais e revistas;15/09/2026;80,00\n"
        )
        destino = Path(self.id().replace(".", "_") + ".zip")
        try:
            with zipfile.ZipFile(destino, "w") as arquivo:
                arquivo.writestr("despesas_contratadas_candidatos_2026_BRASIL.csv", csv.encode("latin-1"))
            candidatos = pd.DataFrame(
                [
                    {"sequencial": "10", "partido": "PT", "uf": "SP", "numero": "1234", "nome_urna": "JOÃO", "nome": "João"},
                    {"sequencial": "20", "partido": "PL", "uf": "RJ", "numero": "2222", "nome_urna": "MARIA", "nome": "Maria"},
                    {"sequencial": "40", "partido": "MDB", "uf": "MG", "numero": "3333", "nome_urna": "PEDRO", "nome": "Pedro"},
                ]
            )
            gastos, categorias, resumo = _acumular_despesas(destino, {"10", "20", "40"}, date(2026, 9, 28))
            relatorio = montar_gastos(candidatos, gastos, categorias, resumo, 2026, date(2026, 9, 28))
        finally:
            destino.unlink(missing_ok=True)

        valores = dict(zip(relatorio.por_candidato["sequencial"], relatorio.por_candidato["gasto_publicidade"]))
        self.assertAlmostEqual(valores["10"], 1000.50)
        self.assertAlmostEqual(valores["20"], 10.00)
        self.assertAlmostEqual(valores["40"], 0.0)
        self.assertEqual(resumo["apos_corte"], 2)
        self.assertEqual(resumo["sem_data"], 1)
        self.assertNotIn("30", valores)


class ComparacaoTeste(unittest.TestCase):
    def test_quem_saiu_quem_entrou_e_troca_de_partido(self):
        anterior = pd.DataFrame(
            [
                {"sequencial": "1", "titulo": "111", "cpf": "12345678901", "nome": "Ana", "nome_urna": "ANA", "uf": "SP", "partido": "PT", "nascimento": "01/01/1980", "resultado": "ELEITO POR QP"},
                {"sequencial": "2", "titulo": "222", "cpf": "10987654321", "nome": "Bruno", "nome_urna": "BRUNO", "uf": "RJ", "partido": "PL", "nascimento": "02/02/1970", "resultado": "ELEITO POR QP"},
                {"sequencial": "3", "titulo": "", "cpf": "", "nome": "Carla Dias", "nome_urna": "CARLA", "uf": "MG", "partido": "MDB", "nascimento": "03/03/1990", "resultado": "ELEITO POR MÉDIA"},
            ]
        )
        atual = pd.DataFrame(
            [
                {"sequencial": "8", "titulo": "111", "cpf": "12345678901", "nome": "Ana", "nome_urna": "ANA", "uf": "SP", "partido": "PL", "nascimento": "01/01/1980", "resultado": ""},
                {"sequencial": "9", "titulo": "", "cpf": "", "nome": "Carla Dias", "nome_urna": "CARLA", "uf": "MG", "partido": "MDB", "nascimento": "1990-03-03", "resultado": ""},
                {"sequencial": "10", "titulo": "444", "cpf": "55566677788", "nome": "Davi", "nome_urna": "DAVI", "uf": "BA", "partido": "PSB", "nascimento": "04/04/1985", "resultado": ""},
            ]
        )
        comparacao = comparar_disputas(anterior, atual)
        self.assertEqual(set(comparacao.sairam["nome"]), {"Bruno"})
        self.assertEqual(set(comparacao.entraram["nome"]), {"Davi"})
        self.assertEqual(set(comparacao.continuam["nome"]), {"Ana", "Carla Dias"})
        self.assertEqual(set(comparacao.mudaram_de_partido["nome"]), {"Ana"})
        self.assertEqual(list(comparacao.mudaram_de_partido["partido_2026"]), ["PL"])
        self.assertEqual(set(comparacao.eleitos_que_nao_concorrem["nome"]), {"Bruno"})
        self.assertEqual(int(resumo_por_partido(comparacao.sairam).loc[0, "candidatos"]), 1)

    def test_deputado_atual_fora_da_disputa(self):
        deputados = pd.DataFrame(
            [
                {"nome": "Ana", "nome_eleitoral": "ANA", "nome_civil": "Ana Souza", "partido": "PT", "uf": "SP", "cpf": "12345678901", "nascimento": "1980-01-01"},
                {"nome": "Bruno", "nome_eleitoral": "BRUNO", "nome_civil": "Bruno Lima", "partido": "PL", "uf": "RJ", "cpf": "10987654321", "nascimento": "1970-02-02"},
            ]
        )
        candidatos = pd.DataFrame(
            [
                {"nome": "Ana Souza", "nome_urna": "ANA", "partido": "PT", "uf": "SP", "cpf": "123.456.789-01", "titulo": "111", "nascimento": "01/01/1980"},
            ]
        )
        cruzamento = cruzar_deputados(deputados, candidatos)
        self.assertEqual(list(cruzamento.na_disputa_2026["nome"]), ["Ana"])
        self.assertEqual(list(cruzamento.fora_da_disputa_2026["nome"]), ["Bruno"])


if __name__ == "__main__":
    unittest.main()
