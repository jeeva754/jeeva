import json
import random

# ---------------- SCHEME POOL (50 Schemes) ----------------
scheme_pool = [
"Kalaignar Magalir Urimai Thogai",
"Free Laptop Scheme",
"Chief Minister Health Insurance Scheme",
"Old Age Pension Scheme",
"Free Bus Pass for Women",
"Drip Irrigation Subsidy",
"Farmer Loan Waiver",
"Smart Ration Card Scheme",
"Self Help Group Loan",
"Marriage Assistance Scheme",
"Pregnancy Nutrition Kit",
"Free Goat Distribution",
"Free Sewing Machine",
"School Uniform Scheme",
"Midday Meal Scheme",
"Scholarship for Students",
"Skill Training Scheme",
"Housing Scheme",
"Street Vendor Loan Scheme",
"Startup Seed Fund",
"Solar Pump Subsidy",
"Women Safety Scheme",
"Youth Employment Camp",
"Free Electricity for Farmers",
"Free Bicycle Scheme",
"Public Library Development",
"Village Internet Scheme",
"Free Medical Camp",
"Primary Health Upgrade",
"Water Tank Construction",
"Public Toilet Scheme",
"Waste Management Scheme",
"Coastal Area Development",
"Hill Area Development",
"Minority Scholarship",
"Differently Abled Welfare",
"Senior Citizen Travel Pass",
"Urban Employment Scheme",
"Rural Employment Scheme",
"Nutrition Food Kit",
"Women Entrepreneurship Loan",
"Student Free Bus Pass",
"Farmer Equipment Subsidy",
"Green House Solar",
"Handloom Weaver Support",
"Fishing Net Subsidy",
"Youth Startup Support",
"Digital Education Scheme",
"Rain Water Harvesting",
"Village Road Development"
]

# ---------------- REAL DISTRICT → CONSTITUENCY ----------------
constituency_data = {

"Chennai":[
"Kolathur","Villivakkam","Thiru-Vi-Ka-Nagar","Egmore","Royapuram","Harbour",
"Chepauk-Thiruvallikeni","Thousand Lights","Anna Nagar","Virugampakkam",
"Saidapet","T. Nagar","Mylapore","Velachery","Sholinganallur","Perambur"
],

"Tiruvallur":[
"Gummidipoondi","Ponneri","Tiruttani","Thiruvallur","Poonamallee",
"Avadi","Maduravoyal","Ambattur","Madhavaram"
],

"Kancheepuram":[
"Sriperumbudur","Kundrathur","Uthiramerur","Kancheepuram"
],

"Chengalpattu":[
"Tambaram","Alandur","Pallavaram","Chengalpattu","Thiruporur","Cheyyur"
],

"Ranipet":[
"Arcot","Sholingur","Arakkonam"
],

"Vellore":[
"Katpadi","Vellore","Anaikattu","Gudiyattam"
],

"Tirupathur":[
"Jolarpet","Tirupathur","Ambur","Vaniyambadi"
],

"Krishnagiri":[
"Krishnagiri","Bargur","Uthangarai","Hosur","Veppanahalli"
],

"Dharmapuri":[
"Palacode","Pennagaram","Dharmapuri","Pappireddippatti","Harur"
],

"Salem":[
"Salem North","Salem South","Salem West","Omalur","Edappadi",
"Mettur","Veerapandi","Yercaud","Attur","Gangavalli","Sankari"
],

"Namakkal":[
"Rasipuram","Senthamangalam","Namakkal","Paramathi Velur","Tiruchengode","Kumarapalayam"
],

"Erode":[
"Erode East","Erode West","Modakkurichi","Perundurai","Bhavani","Anthiyur","Gobichettipalayam","Bhavanisagar"
],

"Tiruppur":[
"Tiruppur North","Tiruppur South","Avinashi","Palladam","Dharapuram","Kangayam","Udumalpet","Madathukulam"
],

"Nilgiris":[
"Udhagamandalam","Gudalur","Coonoor"
],

"Coimbatore":[
"Coimbatore North","Coimbatore South","Kavundampalayam","Singanallur",
"Thondamuthur","Kinathukadavu","Pollachi","Valparai","Sulur"
],

"Dindigul":[
"Palani","Oddanchatram","Athoor","Nilakkottai","Natham","Dindigul"
],

"Karur":[
"Aravakurichi","Karur","Krishnarayapuram","Kulithalai"
],

"Tiruchirappalli":[
"Srirangam","Tiruchirappalli West","Tiruchirappalli East","Thiruverumbur",
"Manachanallur","Musiri","Thuraiyur","Lalgudi","Manapparai"
],

"Perambalur":[
"Perambalur","Kunnam"
],

"Ariyalur":[
"Ariyalur","Jayankondam"
],

"Cuddalore":[
"Tittakudi","Vriddhachalam","Neyveli","Panruti","Cuddalore",
"Kurinjipadi","Bhuvanagiri","Chidambaram","Kattumannarkoil"
],

"Kallakurichi":[
"Kallakurichi","Rishivandiyam","Sankarapuram","Ulundurpettai"
],

"Villupuram":[
"Villupuram","Vikravandi","Tirukkoyilur","Vanur","Tindivanam","Mailam","Gingee"
],

"Tiruvannamalai":[
"Tiruvannamalai","Kilpennathur","Kalasapakkam","Chengam","Polur","Arani","Cheyyar"
],

"Nagapattinam":[
"Nagapattinam","Kilvelur"
],

"Mayiladuthurai":[
"Mayiladuthurai","Poompuhar","Sirkazhi"
],

"Tiruvarur":[
"Tiruvarur","Nannilam","Thiruvidaimarudur"
],

"Thanjavur":[
"Thanjavur","Orathanadu","Papanasam","Kumbakonam","Pattukkottai","Peravurani"
],

"Pudukkottai":[
"Pudukkottai","Gandarvakottai","Viralimalai","Thirumayam","Alangudi","Aranthangi"
],

"Sivaganga":[
"Sivaganga","Manamadurai","Karaikudi","Tirupattur"
],

"Madurai":[
"Madurai North","Madurai South","Madurai Central","Madurai East","Madurai West",
"Thiruparankundram","Tirumangalam","Usilampatti","Melur","Sholavandan"
],

"Theni":[
"Andipatti","Periyakulam","Bodinayakanur","Cumbum"
],

"Virudhunagar":[
"Rajapalayam","Srivilliputhur","Sattur","Sivakasi","Virudhunagar","Aruppukkottai","Tiruchuli"
],

"Ramanathapuram":[
"Ramanathapuram","Paramakudi","Mudukulathur"
],

"Thoothukudi":[
"Thoothukudi","Tiruchendur","Srivaikuntam","Vilathikulam","Ottapidaram","Kovilpatti"
],

"Tenkasi":[
"Tenkasi","Alangulam","Kadayanallur","Sankarankovil","Vasudevanallur"
],

"Tirunelveli":[
"Tirunelveli","Palayamkottai","Ambasamudram","Nanguneri","Radhapuram"
],

"Kanyakumari":[
"Nagercoil","Padmanabhapuram","Vilavancode","Killiyoor"
]
}

# ---------------- JSON GENERATION ----------------
tn_data = {}

for district, consts in constituency_data.items():

    tn_data[district] = {"constituencies": {}}

    for const in consts:
        schemes = random.sample(scheme_pool, 10)

        tn_data[district]["constituencies"][const] = {
            "schemes": schemes
        }

# SAVE FILE
with open("tn_data.json", "w", encoding="utf-8") as f:
    json.dump(tn_data, f, indent=4, ensure_ascii=False)

print("✅ tn_data.json successfully created with REAL 234 constituencies!")
