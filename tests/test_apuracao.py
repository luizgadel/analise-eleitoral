import unittest

from eleitoral.apuracao import aplicar_snapshot, voto_valido


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
