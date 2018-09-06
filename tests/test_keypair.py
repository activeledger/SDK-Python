import sys 
sys.path.append('/home/jialin/Documents/python-sdk/src/')

from activeledgersdk.primitives import keypairs
import unittest

class KeyGenerationTest(unittest.TestCase):

    # testing case on key length
    key_length_not_ok = (0, 100, 500, 700, 1024)
    key_lenth_ok = (1025, 2000, 2048, 3000)
    # testing case on key type
    key_type_not_ok = ('esc', 'aab', 'abc')
    key_type_ok = ('rsa', 'secp256k1')
    


    def test_keysize_not_ok(self):
        for size in self.key_length_not_ok:
            self.assertRaises(ValueError, keypairs.generate, keytype = 'rsa' , keysize = size)
    
    def test_keysize_ok(self):
        for size in self.key_lenth_ok:
            self.assertIsNotNone(keypairs.generate('rsa', size))
    
    def test_keytype_not_ok(self):
        for ktype in self.key_type_not_ok:
            self.assertRaises(ValueError, keypairs.generate, keytype = ktype)
    
    def test_keytype_ok(self):
        for ktype in self.key_type_ok:
            self.assertIsNotNone(keypairs.generate(ktype))
    
    def test_key_verify(self):
        for ktype in self.key_type_ok:
            k_object = keypairs.generate(ktype)
            self.assertTrue(keypairs.verify(ktype, k_object))
    

if __name__ == '__main__':
    unittest.main()
