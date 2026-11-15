"""Тесты: python -m unittest discover -s tests"""
import os, sys, unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from sakha_normalizer import Normalizer

N = Normalizer()


class TestSakha(unittest.TestCase):
    def check(self, src, want):
        self.assertEqual(N.normalize(src), want)

    def test_digits(self):
        self.check('ба5ар', 'баҕар')
        self.check('8йдөө', 'өйдөө')

    def test_russian_letters(self):
        self.check('согус', 'соҕус')
        self.check('санга дьиэ', 'саҥа дьиэ')
        self.check('оскуолага', 'оскуолаҕа')

    def test_soft_sign_as_shha(self):
        self.check('баьылык', 'баһылык')
        self.check('биьиэхэ', 'биһиэхэ')

    def test_latin(self):
        self.check('Yрдyк', 'Үрдүк')
        self.check('баhылык', 'баһылык')

    def test_case_kept(self):
        self.check('Согус', 'Соҕус')

    def test_correct_text_untouched(self):
        s = 'Бу суруйуубар мээнэҕэ үрдүк сололоох дьону аҕалбатым.'
        self.check(s, s)


class TestDoNotTouch(unittest.TestCase):
    def same(self, s):
        self.assertEqual(N.normalize(s), s)

    def test_russian(self):
        self.same('Он сказал что все нормально, завтра приедет')
        self.same('Сон был хороший, но короткий')

    def test_russian_with_sakha_endings(self):
        self.same('колодкалар баар дуо?')
        self.same('заказыҥ кэллэ')

    def test_latin_brands_abbr_numbers(self):
        self.same('WhatsApp-ка ыыт')
        self.same('ИП Иванов, ООО Ромашка')
        self.same('резина 205/55 R16, 5шт, 10к')

    def test_links(self):
        self.same('https://ysia.ru/5ff ону көр, @user_5 #саха5')

    def test_empty(self):
        self.same('')
        self.same('   \n')


if __name__ == '__main__':
    unittest.main()
