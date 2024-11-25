def jumlahEmberAirPenuh(emberAirPenuh, aturan):
    hasil = emberAirPenuh
    tampung = 0
    while emberAirPenuh:
        hasil = hasil + int(emberAirPenuh/aturan)
        emberAirPenuh = int(emberAirPenuh/aturan)
        print("Hasil", hasil)
        if emberAirPenuh < aturan:
            break
    
    return hasil

print(jumlahEmberAirPenuh(9, 3))