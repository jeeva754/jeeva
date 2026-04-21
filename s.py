import json

# Load your existing JSON file
file_path = 'tamilnadu_complete_v2.json'
with open(file_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

# Complete taluk mapping for all 38 districts (fill in all taluks)
taluk_mapping = {
    "Ariyalur district": ["Ariyalur", "Udayarpalayam", "Sendurai", "Andimadam"],
    "Chennai district": ["Alandur", "Ambattur", "Aminjikarai", "Ayanavaram", "Egmore"],
    "Coimbatore district": ["Coimbatore North", "Coimbatore South", "Pollachi", "Mettupalayam"],
    "Cuddalore district": ["Cuddalore", "Bhuvanagiri", "Chidambaram", "Panruti", "Kurinjipadi"],
    "Dharmapuri district": ["Dharmapuri", "Pappireddipatti", "Harur", "Palacode"],
    "Dindigul district": ["Dindigul", "Palani", "Oddanchatram", "Kodaikanal"],
    "Erode district": ["Erode", "Bhavani", "Gobichettipalayam", "Sathyamangalam"],
    "Kanchipuram district": ["Kanchipuram", "Sriperumbudur", "Uthiramerur", "Cheyyar"],
    "Kanyakumari district": ["Nagercoil", "Thovalai", "Agastheeswaram", "Kottar"],
    "Karur district": ["Karur", "Krishnarayapuram", "Kulithalai", "Manmangalam"],
    "Krishnagiri district": ["Krishnagiri", "Hosur", "Pochampalli", "Uthangarai"],
    "Madurai district": ["Madurai North", "Madurai South", "Melur", "Vadipatti", "Usilampatti"],
    "Nagapattinam district": ["Nagapattinam", "Kilvelur", "Vedaranyam", "Thirukkuvalai"],
    "Namakkal district": ["Namakkal", "Rasipuram", "Paramathi Velur", "Senthamangalam"],
    "Perambalur district": ["Perambalur", "Veppanthattai", "Kunnam", "Alathur"],
    "Pudukkottai district": ["Pudukkottai", "Aranthangi", "Alangudi", "Thirumayam"],
    "Ramanathapuram district": ["Ramanathapuram", "Rameswaram", "Paramakudi", "Kadaladi"],
    "Salem district": ["Salem", "Omalur", "Mettur", "Attur", "Edappadi"],
    "Sivaganga district": ["Sivaganga", "Tirupathur", "Karaikudi", "Manamadurai"],
    "Tenkasi district": ["Tenkasi", "Sankarankovil", "Vasudevanallur", "Kadayanallur"],
    "Thanjavur district": ["Thanjavur", "Papanasam", "Kumbakonam", "Orathanadu"],
    "Theni district": ["Theni", "Periyakulam", "Bodinayakanur", "Andipatti"],
    "Thiruvallur district": ["Thiruvallur", "Ponneri", "Uthukkottai", "Gummidipoondi"],
    "Thiruvarur district": ["Thiruvarur", "Nannilam", "Needamangalam", "Mannargudi"],
    "Thoothukudi district": ["Thoothukudi", "Sathankulam", "Kovilpatti", "Srivaikundam"],
    "Tiruchirappalli district": ["Tiruchirappalli", "Srirangam", "Lalgudi", "Manapparai"],
    "Tirunelveli district": ["Tirunelveli", "Palayamkottai", "Ambasamudram", "Tenkasi"],
    "Tirupattur district": ["Tirupattur", "Vaniyambadi", "Natrampalli", "Jolarpettai"],
    "Tiruppur district": ["Tiruppur", "Udumalpet", "Avinashi", "Kangeyam"],
    "Tiruvannamalai district": ["Tiruvannamalai", "Cheyyar", "Arani", "Chengam"],
    "Vellore district": ["Vellore", "Katpadi", "Gudiyatham", "Walajapet"],
    "Villupuram district": ["Villupuram", "Tindivanam", "Gingee", "Vanur"],
    "Virudhunagar district": ["Virudhunagar", "Sathur", "Rajapalayam", "Aruppukottai"],
    "Kallakurichi district": ["Kallakurichi", "Sankarapuram", "Chinnasalem", "Ulundurpettai"],
    "Ranipet district": ["Ranipet", "Arakkonam", "Walajapet", "Nemili"]
}

# Update the data structure
for district in data['TamilNadu']['districts']:
    name = district['name_en']
    if name in taluk_mapping:
        district['taluks'] = taluk_mapping[name]

# Save the updated JSON
output_path = 'tamilnadu_updated.json'
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"Successfully updated {output_path}")
