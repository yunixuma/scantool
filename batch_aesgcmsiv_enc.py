import os, sys
import datetime, time
import my_common as my
import myenclib

def batch_aesgcmsiv_enc(lst, key):
    name_plain = list(lst[0].keys())[0]
    for i in range(len(lst)):
        nonce, ciphertext = myenclib.aesgcmsiv_enc(key, lst[i][name_plain].encode('utf-8'))
        encoded_data = myenclib.aesgcm_enc_b64(nonce, ciphertext)
        lst[i]['encdata'] = encoded_data
        print(lst[i])
    return lst

def wrapper(args):
    if args and len(args) > 2 and len(args[1]) >= 16:
        key = myenclib.b64_dec(args[2])
    else:
        key = myenclib.aesgcmsiv_gen_key()
    print(f"Secret Key (Base64): {myenclib.b64_enc(key)}")
    if args and len(args) > 1:
        lst = my.load_csv(args[1])
    else:
        lst = my.load_csv("plain.txt")
    return batch_aesgcmsiv_enc(lst, key)

if __name__ == "__main__":
    start_at = datetime.datetime.now()

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    data_dir = BASE_DIR + "/data"
    my.mkdir(data_dir, True)
    date = my.get_datetime()
    filepath = "cipher_" + date + ".csv"
    filepath = data_dir + "/" + filepath

    ret = wrapper(sys.argv)
    # print(ret)
    my.save_csv(ret, filepath)

    finish_at = datetime.datetime.now()
    print(f"Elapsed time: {finish_at - start_at}")
