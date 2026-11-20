import unittest

from plain_title import plain_title

BODY = ("A Polícia Rodoviária Federal (PRF) iniciou nesta quinta a operação do feriado da Consciência Negra, "
        "que reforça a fiscalização nas rodovias até domingo. O dólar fechou a R$ 5,86. GTA VI saiu nos EUA.")


class PlainTitleTests(unittest.TestCase):
    def test_caps_title_uses_casing_from_body(self):
        self.assertEqual(
            plain_title("PRF REFORÇA FISCALIZAÇÃO NAS RODOVIAS ATÉ DOMINGO NO FERIADO DA CONSCIÊNCIA NEGRA", BODY),
            "PRF reforça fiscalização nas rodovias até domingo no feriado da Consciência Negra")

    def test_first_word_capitalized_and_unknown_words_lower(self):
        self.assertEqual(plain_title("OPERAÇÃO SURPREENDE A PRF", BODY), "Operação surpreende a PRF")

    def test_numbers_symbols_and_acronyms(self):
        self.assertEqual(plain_title("DÓLAR FECHA A R$ 5,86; GTA VI CHEGA AOS EUA", BODY),
                         "Dólar fecha a R$ 5,86; GTA VI chega aos EUA")

    def test_sentence_start_compounds_mixed_case_and_corpus(self):
        body = ("Após a reunião, a União Europeia e o JPMorgan falaram. Agências citam a Série A. "
                "A economia europeia e a série histórica seguem.")
        corpus = "Os EUA e a ONU discutem."
        self.assertEqual(
            plain_title("UNIÃO EUROPEIA E JPMORGAN FALAM APÓS ALERTA DE AGÊNCIAS SOBRE A SÉRIE A, DIZEM EUA E ONU", body, corpus),
            "União Europeia e JPMorgan falam após alerta de agências sobre a Série A, dizem EUA e ONU")

    def test_next_word_pair_and_unknown_short_acronyms(self):
        body = "Eles são muitos. Choveu em São Paulo."
        self.assertEqual(plain_title("TEMPORAIS EM SÃO PAULO; PS5 E G20", body), "Temporais em São Paulo; PS5 e G20")

    def test_normal_title_untouched(self):
        self.assertEqual(plain_title("Fachin retira sigilo de relatório", BODY), "Fachin retira sigilo de relatório")
        self.assertEqual(plain_title("", BODY), "")


if __name__ == "__main__":
    unittest.main()
