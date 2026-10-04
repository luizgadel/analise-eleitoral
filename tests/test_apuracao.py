import unittest

from eleitoral.apuracao import aplicar_snapshot, cadeiras_no_instante, voto_valido


def _bruto(and_flag: str) -> dict:
    return {
        "and": and_flag,
        "dt": "04/10/2026",
        "ht": "22:00:00",
        "s": {"pst": "100,00", "st": "8157", "ts": "8157"},
        "v": {"vnom": "1000"},
        "carg": [
            {
                "cd": "6",
                "qe": "100",
                "nv": "8",
                "fed": [{"n": "101", "sg": "PT/PC do B/PV", "npar": ["13", "43"]}],
                "agr": [
                    {
                        "par": [
                            {
                                "sg": "PT",
                                "nfed": "101",
                                "tvtn": "60",
                                "cand": [
                                    {
                                        "sqcand": "1",
                                        "n": "1313",
                                        "vap": "70",
                                        "dvt": "Válido",
                                        "pvap": "1,00",
                                        "e": "s",
                                        "st": "Eleito",
                                    }
                                ],
                            },
                            {
                                "sg": "PC do B",
                                "nfed": "101",
                                "tvtn": "40",
                                "cand": [
                                    {
                                        "sqcand": "2",
                                        "n": "4343",
                                        "vap": "50",
                                        "dvt": "Anulado sub judice",
                                        "pvap": "0,50",
                                        "e": "n",
                                        "st": "",
                                    }
                                ],
                            },
                            {
                                "sg": "PSTU",
                                "nfed": "",
                                "tvtn": "10",
                                "cand": [
                                    {
                                        "sqcand": "3",
                                        "n": "1616",
                                        "vap": "10",
                                        "dvt": "Válido",
                                        "pvap": "0,10",
                                        "e": "n",
                                        "st": "",
                                    }
                                ],
                            },
                        ]
                    }
                ],
            }
        ],
    }


class ApuracaoTeste(unittest.TestCase):
    def test_voto_anulado_nao_entra(self):
        self.assertEqual(voto_valido({"dvt": "Válido", "vap": "70"}), 70)
        self.assertEqual(voto_valido({"dvt": "Anulado sub judice", "vap": "50"}), 0)
        self.assertEqual(voto_valido({"dvt": "Válido (legenda)", "vap": "12"}), 0)

    def test_apuracao_aberta_nao_altera_o_painel(self):
        painel = {"desempenho": [{"concorre2026": True, "numero": "1616", "votos": 10}], "quociente2026": None}
        self.assertFalse(aplicar_snapshot(painel, _bruto("p")))
        self.assertEqual(painel["desempenho"][0]["votos"], 10)
        self.assertNotIn("votos2026", painel["desempenho"][0])
        self.assertIsNone(painel["quociente2026"])

    def test_snapshot_fechado_grava_2026_e_preserva_2022(self):
        painel = {
            "desempenho": [
                {"concorre2026": True, "sequencial2026": "1", "numero2026": "9999", "numero": "1313", "votos": 10},
                {"concorre2026": True, "numero2026": "4343", "votos": 3},
                {"concorre2026": True, "numero": "1616", "votos": None},
                {"concorre2026": False, "numero": "2210", "votos": 8},
            ]
        }
        self.assertTrue(aplicar_snapshot(painel, _bruto("f")))
        por_seq, anulado, pstu, fora = painel["desempenho"]
        self.assertEqual(por_seq["votos"], 10)
        self.assertEqual(por_seq["votos2026"], 70)
        self.assertTrue(por_seq["eleito2026"])
        self.assertEqual(por_seq["situacao2026"], "Eleito")
        self.assertEqual(anulado["votos"], 3)
        self.assertEqual(anulado["votos2026"], 0)
        self.assertFalse(anulado["eleito2026"])
        self.assertEqual(pstu["votos"], None)
        self.assertEqual(pstu["votos2026"], 10)
        self.assertEqual(fora["votos"], 8)
        self.assertNotIn("votos2026", fora)
        federacoes = {item["nome"]: item["votos"] for item in painel["quociente2026"]["federacoes"]}
        self.assertEqual(federacoes["PT/PC do B/PV"], 100)
        self.assertEqual(federacoes["PSTU"], 10)
        self.assertEqual(painel["quociente2026"]["qe"], 100)
        self.assertEqual(painel["quociente2026"]["carimbo"], "04/10/2026 22:00:00")


def _legenda(nome: str, votos: int, partidos: list[str] | None = None) -> dict:
    return {"nome": nome, "partidos": partidos or [nome], "votosCadeiras": votos}


def _cand(identificador: str, partido: str, votos: int) -> dict:
    return {"id": identificador, "partido": partido, "votos": votos}


class CadeirasTeste(unittest.TestCase):
    def test_quociente_partidario_exige_dez_por_cento(self):
        eleitos = cadeiras_no_instante(
            [_legenda("A", 250), _legenda("B", 40)],
            [_cand("a1", "A", 40), _cand("a2", "A", 15), _cand("a3", "A", 9), _cand("b1", "B", 30)],
            qe=100,
            vagas=2,
        )
        self.assertEqual(eleitos, {"a1", "a2"})

    def test_sobra_80_20_pula_candidato_abaixo_de_vinte(self):
        eleitos = cadeiras_no_instante(
            [_legenda("A", 250), _legenda("B", 80)],
            [_cand("a1", "A", 40), _cand("a2", "A", 15), _cand("a3", "A", 5), _cand("b1", "B", 25)],
            qe=100,
            vagas=3,
        )
        self.assertEqual(eleitos, {"a1", "a2", "b1"})

    def test_ultima_fase_abre_para_quem_nao_tem_oitenta(self):
        eleitos = cadeiras_no_instante(
            [_legenda("A", 250), _legenda("B", 79)],
            [_cand("a1", "A", 40), _cand("a2", "A", 15), _cand("b1", "B", 19)],
            qe=100,
            vagas=3,
        )
        self.assertEqual(eleitos, {"a1", "a2", "b1"})

    def test_federacao_junta_os_partidos_e_nao_passa_das_vagas(self):
        eleitos = cadeiras_no_instante(
            [_legenda("PT/PV", 300, ["PT", "PV"])],
            [_cand("pt", "PT", 40), _cand("pv", "PV", 30), _cand("extra", "PT", 20)],
            qe=100,
            vagas=2,
        )
        self.assertEqual(eleitos, {"pt", "pv"})

    def test_sem_quociente_ninguem_leva_cadeira(self):
        self.assertEqual(cadeiras_no_instante([_legenda("A", 100)], [_cand("a", "A", 100)], qe=0, vagas=8), set())
