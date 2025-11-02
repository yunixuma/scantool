import os, sys
import datetime, time
import my_common as my
import myenclib
import batch_aesgcmsiv_enc
import dm_gen

def wrapper(args):
    if args and len(args) > 2 and len(args[2]) >= 16:
        key = myenclib.b64_dec(args[2], True)
    else:
        key = myenclib.aesgcmsiv_gen_key()
    print(f"Secret Key (Base64): {myenclib.b64_enc(key, True)}")
    if args and len(args) > 1:
        path_plain = args[1]
    else:
        path_plain = "plain.txt"
    plains = my.load_csv(path_plain)
    ciphers = batch_aesgcmsiv_enc.batch_aesgcmsiv_enc(plains, key)
    # name_plain = list(plains[0].keys())[0]
    for i in range(len(ciphers)):
        image_datum = dm_gen.generate_datamatrix_base64(ciphers[i]['encdata'])
        plains[i]['image'] = myenclib.b64_enc(image_datum)
        # images.append( {
        #     'text': plains[i][name_plain],
        #     'image': myenclib.b64_enc(image_datum)
        # } )
    return plains

if __name__ == "__main__":
    start_at = datetime.datetime.now()

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    data_dir = BASE_DIR + "/data"
    my.mkdir(data_dir, True)
    date = my.get_datetime()
    filepath = "image_" + date + ".csv"
    filepath = data_dir + "/" + filepath

    ret = wrapper(sys.argv)
    # print(ret)
    my.save_csv(ret, filepath)

    finish_at = datetime.datetime.now()
    print(f"Elapsed time: {finish_at - start_at}")
