import dash
from dash import dcc, html, Input, Output, State
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import math
import time
from urllib.parse import parse_qs

# Import the enhanced BigQuery radar chart functions
try:
    from enhanced_radar_v2_with_fast_state import (
        BigQueryRadarChartDataProvider,
        create_enhanced_radar_chart,
        create_detail_chart,
        get_performance_label
    )
    ENHANCED_V2_AVAILABLE = True
    print("✅ Enhanced BigQuery radar chart functions imported successfully")
except ImportError as e:
    print(f"⚠️  Enhanced V2 functions not available: {e}")
    ENHANCED_V2_AVAILABLE = False

import os

# BigQuery connection parameters
PROJECT_ID = os.environ.get('BIGQUERY_PROJECT', 'county-dashboard')
DATASET_ID = os.environ.get('BIGQUERY_DATASET', 'sustainability_data')

# County-specific password configuration
COUNTY_PASSWORDS = {
    '01001': 'autauga2024',  # Autauga County, AL
    '01003': 'baldwin2024',  # Baldwin County, AL
    '01005': 'barbour2024',  # Barbour County, AL
    '01005': 'barbour2024', #Barbour County, AL
    '01007': 'bibb2024', #Bibb County, AL
    '01009': 'blount2024', #Blount County, AL
    '01011': 'bullock2024', #Bullock County, AL
    '01013': 'butler2024', #Butler County, AL
    '01015': 'calhoun2024', #Calhoun County, AL
    '01017': 'chambers2024', #Chambers County, AL
    '01019': 'cherokee2024', #Cherokee County, AL
    '01021': 'chilton2024', #Chilton County, AL
    '01023': 'choctaw2024', #Choctaw County, AL
    '01025': 'clarke2024', #Clarke County, AL
    '01027': 'clay2024', #Clay County, AL
    '01029': 'cleburne2024', #Cleburne County, AL
    '01031': 'coffee2024', #Coffee County, AL
    '01033': 'colbert2024', #Colbert County, AL
    '01035': 'conecuh2024', #Conecuh County, AL
    '01037': 'coosa2024', #Coosa County, AL
    '01039': 'covington2024', #Covington County, AL
    '01041': 'crenshaw2024', #Crenshaw County, AL
    '01043': 'cullman2024', #Cullman County, AL
    '01045': 'dale2024', #Dale County, AL
    '01047': 'dallas2024', #Dallas County, AL
    '01049': 'dekalb2024', #DeKalb County, AL
    '01051': 'elmore2024', #Elmore County, AL
    '01053': 'escambia2024', #Escambia County, AL
    '01055': 'etowah2024', #Etowah County, AL
    '01057': 'fayette2024', #Fayette County, AL
    '01059': 'franklin2024', #Franklin County, AL
    '01061': 'geneva2024', #Geneva County, AL
    '01063': 'greene2024', #Greene County, AL
    '01065': 'hale2024', #Hale County, AL
    '01067': 'henry2024', #Henry County, AL
    '01069': 'houston2024', #Houston County, AL
    '01071': 'jackson2024', #Jackson County, AL
    '01073': 'jefferson2024', #Jefferson County, AL
    '01075': 'lamar2024', #Lamar County, AL
    '01077': 'lauderdale2024', #Lauderdale County, AL
    '01079': 'lawrence2024', #Lawrence County, AL
    '01081': 'lee2024', #Lee County, AL
    '01083': 'limestone2024', #Limestone County, AL
    '01085': 'lowndes2024', #Lowndes County, AL
    '01087': 'macon2024', #Macon County, AL
    '01089': 'madison2024', #Madison County, AL
    '01091': 'marengo2024', #Marengo County, AL
    '01093': 'marion2024', #Marion County, AL
    '01095': 'marshall2024', #Marshall County, AL
    '01097': 'mobile2024', #Mobile County, AL
    '01099': 'monroe2024', #Monroe County, AL
    '01101': 'montgomery2024', #Montgomery County, AL
    '01103': 'morgan2024', #Morgan County, AL
    '01105': 'perry2024', #Perry County, AL
    '01107': 'pickens2024', #Pickens County, AL
    '01109': 'pike2024', #Pike County, AL
    '01111': 'randolph2024', #Randolph County, AL
    '01113': 'russell2024', #Russell County, AL
    '01115': 'st. clair2024', #St. Clair County, AL
    '01117': 'shelby2024', #Shelby County, AL
    '01119': 'sumter2024', #Sumter County, AL
    '01121': 'talladega2024', #Talladega County, AL
    '01123': 'tallapoosa2024', #Tallapoosa County, AL
    '01125': 'tuscaloosa2024', #Tuscaloosa County, AL
    '01127': 'walker2024', #Walker County, AL
    '01129': 'washington2024', #Washington County, AL
    '01131': 'wilcox2024', #Wilcox County, AL
    '01133': 'winston2024', #Winston County, AL
    '02013': 'aleutians east2024', #Aleutians East County, AK
    '02016': 'aleutians west2024', #Aleutians West County, AK
    '02020': 'anchorage2024', #Anchorage County, AK
    '02050': 'bethel2024', #Bethel County, AK
    '02060': 'bristol bay2024', #Bristol Bay County, AK
    '02063': 'chugach census area2024', #Chugach Census Area County, AK
    '02066': 'copper river census area2024', #Copper River Census Area County, AK
    '02068': 'denali2024', #Denali County, AK
    '02070': 'dillingham2024', #Dillingham County, AK
    '02090': 'fairbanks north star2024', #Fairbanks North Star County, AK
    '02100': 'haines2024', #Haines County, AK
    '02105': 'hoonah-angoon2024', #Hoonah-Angoon County, AK
    '02110': 'juneau2024', #Juneau County, AK
    '02122': 'kenai peninsula2024', #Kenai Peninsula County, AK
    '02130': 'ketchikan gateway2024', #Ketchikan Gateway County, AK
    '02150': 'kodiak island2024', #Kodiak Island County, AK
    '02158': 'kusilvak2024', #Kusilvak County, AK
    '02164': 'lake and peninsula2024', #Lake and Peninsula County, AK
    '02170': 'matanuska-susitna2024', #Matanuska-Susitna County, AK
    '02180': 'nome2024', #Nome County, AK
    '02185': 'north slope2024', #North Slope County, AK
    '02188': 'northwest arctic2024', #Northwest Arctic County, AK
    '02195': 'petersburg2024', #Petersburg County, AK
    '02198': 'prince of wales-hyder2024', #Prince of Wales-Hyder County, AK
    '02220': 'sitka2024', #Sitka County, AK
    '02230': 'skagway2024', #Skagway County, AK
    '02240': 'southeast fairbanks2024', #Southeast Fairbanks County, AK
    '02275': 'wrangell2024', #Wrangell County, AK
    '02282': 'yakutat2024', #Yakutat County, AK
    '02290': 'yukon-koyukuk2024', #Yukon-Koyukuk County, AK
    '04001': 'apache2024', #Apache County, AZ
    '04003': 'cochise2024', #Cochise County, AZ
    '04005': 'coconino2024', #Coconino County, AZ
    '04007': 'gila2024', #Gila County, AZ
    '04009': 'graham2024', #Graham County, AZ
    '04011': 'greenlee2024', #Greenlee County, AZ
    '04012': 'la paz2024', #La Paz County, AZ
    '04013': 'maricopa2024', #Maricopa County, AZ
    '04015': 'mohave2024', #Mohave County, AZ
    '04017': 'navajo2024', #Navajo County, AZ
    '04019': 'pima2024', #Pima County, AZ
    '04021': 'pinal2024', #Pinal County, AZ
    '04023': 'santa cruz2024', #Santa Cruz County, AZ
    '04025': 'yavapai2024', #Yavapai County, AZ
    '04027': 'yuma2024', #Yuma County, AZ
    '05001': 'arkansas2024', #Arkansas County, AR
    '05003': 'ashley2024', #Ashley County, AR
    '05005': 'baxter2024', #Baxter County, AR
    '05007': 'benton2024', #Benton County, AR
    '05009': 'boone2024', #Boone County, AR
    '05011': 'bradley2024', #Bradley County, AR
    '05013': 'calhoun2024', #Calhoun County, AR
    '05015': 'carroll2024', #Carroll County, AR
    '05017': 'chicot2024', #Chicot County, AR
    '05019': 'clark2024', #Clark County, AR
    '05021': 'clay2024', #Clay County, AR
    '05023': 'cleburne2024', #Cleburne County, AR
    '05025': 'cleveland2024', #Cleveland County, AR
    '05027': 'columbia2024', #Columbia County, AR
    '05029': 'conway2024', #Conway County, AR
    '05031': 'craighead2024', #Craighead County, AR
    '05033': 'crawford2024', #Crawford County, AR
    '05035': 'crittenden2024', #Crittenden County, AR
    '05037': 'cross2024', #Cross County, AR
    '05039': 'dallas2024', #Dallas County, AR
    '05041': 'desha2024', #Desha County, AR
    '05043': 'drew2024', #Drew County, AR
    '05045': 'faulkner2024', #Faulkner County, AR
    '05047': 'franklin2024', #Franklin County, AR
    '05049': 'fulton2024', #Fulton County, AR
    '05051': 'garland2024', #Garland County, AR
    '05053': 'grant2024', #Grant County, AR
    '05055': 'greene2024', #Greene County, AR
    '05057': 'hempstead2024', #Hempstead County, AR
    '05059': 'hot spring2024', #Hot Spring County, AR
    '05061': 'howard2024', #Howard County, AR
    '05063': 'independence2024', #Independence County, AR
    '05065': 'izard2024', #Izard County, AR
    '05067': 'jackson2024', #Jackson County, AR
    '05069': 'jefferson2024', #Jefferson County, AR
    '05071': 'johnson2024', #Johnson County, AR
    '05073': 'lafayette2024', #Lafayette County, AR
    '05075': 'lawrence2024', #Lawrence County, AR
    '05077': 'lee2024', #Lee County, AR
    '05079': 'lincoln2024', #Lincoln County, AR
    '05081': 'little river2024', #Little River County, AR
    '05083': 'logan2024', #Logan County, AR
    '05085': 'lonoke2024', #Lonoke County, AR
    '05087': 'madison2024', #Madison County, AR
    '05089': 'marion2024', #Marion County, AR
    '05091': 'miller2024', #Miller County, AR
    '05093': 'mississippi2024', #Mississippi County, AR
    '05095': 'monroe2024', #Monroe County, AR
    '05097': 'montgomery2024', #Montgomery County, AR
    '05099': 'nevada2024', #Nevada County, AR
    '05101': 'newton2024', #Newton County, AR
    '05103': 'ouachita2024', #Ouachita County, AR
    '05105': 'perry2024', #Perry County, AR
    '05107': 'phillips2024', #Phillips County, AR
    '05109': 'pike2024', #Pike County, AR
    '05111': 'poinsett2024', #Poinsett County, AR
    '05113': 'polk2024', #Polk County, AR
    '05115': 'pope2024', #Pope County, AR
    '05117': 'prairie2024', #Prairie County, AR
    '05119': 'pulaski2024', #Pulaski County, AR
    '05121': 'randolph2024', #Randolph County, AR
    '05123': 'st. francis2024', #St. Francis County, AR
    '05125': 'saline2024', #Saline County, AR
    '05127': 'scott2024', #Scott County, AR
    '05129': 'searcy2024', #Searcy County, AR
    '05131': 'sebastian2024', #Sebastian County, AR
    '05133': 'sevier2024', #Sevier County, AR
    '05135': 'sharp2024', #Sharp County, AR
    '05137': 'stone2024', #Stone County, AR
    '05139': 'union2024', #Union County, AR
    '05141': 'van buren2024', #Van Buren County, AR
    '05143': 'washington2024', #Washington County, AR
    '05145': 'white2024', #White County, AR
    '05147': 'woodruff2024', #Woodruff County, AR
    '05149': 'yell2024', #Yell County, AR
    '06001': 'alameda2024', #Alameda County, CA
    '06003': 'alpine2024', #Alpine County, CA
    '06005': 'amador2024', #Amador County, CA
    '06007': 'butte2024', #Butte County, CA
    '06009': 'calaveras2024', #Calaveras County, CA
    '06011': 'colusa2024', #Colusa County, CA
    '06013': 'contra costa2024', #Contra Costa County, CA
    '06015': 'del norte2024', #Del Norte County, CA
    '06017': 'el dorado2024', #El Dorado County, CA
    '06019': 'fresno2024', #Fresno County, CA
    '06021': 'glenn2024', #Glenn County, CA
    '06023': 'humboldt2024', #Humboldt County, CA
    '06025': 'imperial2024', #Imperial County, CA
    '06027': 'inyo2024', #Inyo County, CA
    '06029': 'kern2024', #Kern County, CA
    '06031': 'kings2024', #Kings County, CA
    '06033': 'lake2024', #Lake County, CA
    '06035': 'lassen2024', #Lassen County, CA
    '06037': 'los angeles2024', #Los Angeles County, CA
    '06039': 'madera2024', #Madera County, CA
    '06041': 'marin2024', #Marin County, CA
    '06043': 'mariposa2024', #Mariposa County, CA
    '06045': 'mendocino2024', #Mendocino County, CA
    '06047': 'merced2024', #Merced County, CA
    '06049': 'modoc2024', #Modoc County, CA
    '06051': 'mono2024', #Mono County, CA
    '06053': 'monterey2024', #Monterey County, CA
    '06055': 'napa2024', #Napa County, CA
    '06057': 'nevada2024', #Nevada County, CA
    '06059': 'orange2024', #Orange County, CA
    '06061': 'placer2024', #Placer County, CA
    '06063': 'plumas2024', #Plumas County, CA
    '06065': 'riverside2024', #Riverside County, CA
    '06067': 'sacramento2024', #Sacramento County, CA
    '06069': 'san benito2024', #San Benito County, CA
    '06071': 'san bernardino2024', #San Bernardino County, CA
    '06073': 'san diego2024', #San Diego County, CA
    '06075': 'san francisco2024', #San Francisco County, CA
    '06077': 'san joaquin2024', #San Joaquin County, CA
    '06079': 'san luis obispo2024', #San Luis Obispo County, CA
    '06081': 'san mateo2024', #San Mateo County, CA
    '06083': 'santa barbara2024', #Santa Barbara County, CA
    '06085': 'santa clara2024', #Santa Clara County, CA
    '06087': 'santa cruz2024', #Santa Cruz County, CA
    '06089': 'shasta2024', #Shasta County, CA
    '06091': 'sierra2024', #Sierra County, CA
    '06093': 'siskiyou2024', #Siskiyou County, CA
    '06095': 'solano2024', #Solano County, CA
    '06097': 'sonoma2024', #Sonoma County, CA
    '06099': 'stanislaus2024', #Stanislaus County, CA
    '06101': 'sutter2024', #Sutter County, CA
    '06103': 'tehama2024', #Tehama County, CA
    '06105': 'trinity2024', #Trinity County, CA
    '06107': 'tulare2024', #Tulare County, CA
    '06109': 'tuolumne2024', #Tuolumne County, CA
    '06111': 'ventura2024', #Ventura County, CA
    '06113': 'yolo2024', #Yolo County, CA
    '06115': 'yuba2024', #Yuba County, CA
    '08001': 'adams2024', #Adams County, CO
    '08003': 'alamosa2024', #Alamosa County, CO
    '08005': 'arapahoe2024', #Arapahoe County, CO
    '08007': 'archuleta2024', #Archuleta County, CO
    '08009': 'baca2024', #Baca County, CO
    '08011': 'bent2024', #Bent County, CO
    '08013': 'boulder2024', #Boulder County, CO
    '08014': 'broomfield2024', #Broomfield County, CO
    '08015': 'chaffee2024', #Chaffee County, CO
    '08017': 'cheyenne2024', #Cheyenne County, CO
    '08019': 'clear creek2024', #Clear Creek County, CO
    '08021': 'conejos2024', #Conejos County, CO
    '08023': 'costilla2024', #Costilla County, CO
    '08025': 'crowley2024', #Crowley County, CO
    '08027': 'custer2024', #Custer County, CO
    '08029': 'delta2024', #Delta County, CO
    '08031': 'denver2024', #Denver County, CO
    '08033': 'dolores2024', #Dolores County, CO
    '08035': 'douglas2024', #Douglas County, CO
    '08037': 'eagle2024', #Eagle County, CO
    '08039': 'elbert2024', #Elbert County, CO
    '08041': 'el paso2024', #El Paso County, CO
    '08043': 'fremont2024', #Fremont County, CO
    '08045': 'garfield2024', #Garfield County, CO
    '08047': 'gilpin2024', #Gilpin County, CO
    '08049': 'grand2024', #Grand County, CO
    '08051': 'gunnison2024', #Gunnison County, CO
    '08053': 'hinsdale2024', #Hinsdale County, CO
    '08055': 'huerfano2024', #Huerfano County, CO
    '08057': 'jackson2024', #Jackson County, CO
    '08059': 'jefferson2024', #Jefferson County, CO
    '08061': 'kiowa2024', #Kiowa County, CO
    '08063': 'kit carson2024', #Kit Carson County, CO
    '08065': 'lake2024', #Lake County, CO
    '08067': 'la plata2024', #La Plata County, CO
    '08069': 'larimer2024', #Larimer County, CO
    '08071': 'las animas2024', #Las Animas County, CO
    '08073': 'lincoln2024', #Lincoln County, CO
    '08075': 'logan2024', #Logan County, CO
    '08077': 'mesa2024', #Mesa County, CO
    '08079': 'mineral2024', #Mineral County, CO
    '08081': 'moffat2024', #Moffat County, CO
    '08083': 'montezuma2024', #Montezuma County, CO
    '08085': 'montrose2024', #Montrose County, CO
    '08087': 'morgan2024', #Morgan County, CO
    '08089': 'otero2024', #Otero County, CO
    '08091': 'ouray2024', #Ouray County, CO
    '08093': 'park2024', #Park County, CO
    '08095': 'phillips2024', #Phillips County, CO
    '08097': 'pitkin2024', #Pitkin County, CO
    '08099': 'prowers2024', #Prowers County, CO
    '08101': 'pueblo2024', #Pueblo County, CO
    '08103': 'rio blanco2024', #Rio Blanco County, CO
    '08105': 'rio grande2024', #Rio Grande County, CO
    '08107': 'routt2024', #Routt County, CO
    '08109': 'saguache2024', #Saguache County, CO
    '08111': 'san juan2024', #San Juan County, CO
    '08113': 'san miguel2024', #San Miguel County, CO
    '08115': 'sedgwick2024', #Sedgwick County, CO
    '08117': 'summit2024', #Summit County, CO
    '08119': 'teller2024', #Teller County, CO
    '08121': 'washington2024', #Washington County, CO
    '08123': 'weld2024', #Weld County, CO
    '08125': 'yuma2024', #Yuma County, CO
    '09110': 'capitol planning2024', #Capitol Planning County, CT
    '09120': 'greater bridgeport2024', #Greater Bridgeport County, CT
    '09130': 'lower connecticut2024', #Lower Connecticut County, CT
    '09140': 'naugatuck valley2024', #Naugatuck Valley County, CT
    '09150': 'northeastern2024', #Northeastern County, CT
    '09160': 'northwest hills2024', #Northwest Hills County, CT
    '09170': 'south central2024', #South Central County, CT
    '09180': 'southeastern2024', #Southeastern County, CT
    '09190': 'western connecticut2024', #Western Connecticut County, CT
    '10001': 'kent2024', #Kent County, DE
    '10003': 'new castle2024', #New Castle County, DE
    '10005': 'sussex2024', #Sussex County, DE
    '11001': 'district of columbia2024', #District of Columbia County, Not Found
    '12001': 'alachua2024', #Alachua County, FL
    '12003': 'baker2024', #Baker County, FL
    '12005': 'bay2024', #Bay County, FL
    '12007': 'bradford2024', #Bradford County, FL
    '12009': 'brevard2024', #Brevard County, FL
    '12011': 'broward2024', #Broward County, FL
    '12013': 'calhoun2024', #Calhoun County, FL
    '12015': 'charlotte2024', #Charlotte County, FL
    '12017': 'citrus2024', #Citrus County, FL
    '12019': 'clay2024', #Clay County, FL
    '12021': 'collier2024', #Collier County, FL
    '12023': 'columbia2024', #Columbia County, FL
    '12027': 'desoto2024', #DeSoto County, FL
    '12029': 'dixie2024', #Dixie County, FL
    '12031': 'duval2024', #Duval County, FL
    '12033': 'escambia2024', #Escambia County, FL
    '12035': 'flagler2024', #Flagler County, FL
    '12037': 'franklin2024', #Franklin County, FL
    '12039': 'gadsden2024', #Gadsden County, FL
    '12041': 'gilchrist2024', #Gilchrist County, FL
    '12043': 'glades2024', #Glades County, FL
    '12045': 'gulf2024', #Gulf County, FL
    '12047': 'hamilton2024', #Hamilton County, FL
    '12049': 'hardee2024', #Hardee County, FL
    '12051': 'hendry2024', #Hendry County, FL
    '12053': 'hernando2024', #Hernando County, FL
    '12055': 'highlands2024', #Highlands County, FL
    '12057': 'hillsborough2024', #Hillsborough County, FL
    '12059': 'holmes2024', #Holmes County, FL
    '12061': 'indian river2024', #Indian River County, FL
    '12063': 'jackson2024', #Jackson County, FL
    '12065': 'jefferson2024', #Jefferson County, FL
    '12067': 'lafayette2024', #Lafayette County, FL
    '12069': 'lake2024', #Lake County, FL
    '12071': 'lee2024', #Lee County, FL
    '12073': 'leon2024', #Leon County, FL
    '12075': 'levy2024', #Levy County, FL
    '12077': 'liberty2024', #Liberty County, FL
    '12079': 'madison2024', #Madison County, FL
    '12081': 'manatee2024', #Manatee County, FL
    '12083': 'marion2024', #Marion County, FL
    '12085': 'martin2024', #Martin County, FL
    '12086': 'miami-dade2024', #Miami-Dade County, FL
    '12087': 'monroe2024', #Monroe County, FL
    '12089': 'nassau2024', #Nassau County, FL
    '12091': 'okaloosa2024', #Okaloosa County, FL
    '12093': 'okeechobee2024', #Okeechobee County, FL
    '12095': 'orange2024', #Orange County, FL
    '12097': 'osceola2024', #Osceola County, FL
    '12099': 'palm beach2024', #Palm Beach County, FL
    '12101': 'pasco2024', #Pasco County, FL
    '12103': 'pinellas2024', #Pinellas County, FL
    '12105': 'polk2024', #Polk County, FL
    '12107': 'putnam2024', #Putnam County, FL
    '12109': 'st. johns2024', #St. Johns County, FL
    '12111': 'st. lucie2024', #St. Lucie County, FL
    '12113': 'santa rosa2024', #Santa Rosa County, FL
    '12115': 'sarasota2024', #Sarasota County, FL
    '12117': 'seminole2024', #Seminole County, FL
    '12119': 'sumter2024', #Sumter County, FL
    '12121': 'suwannee2024', #Suwannee County, FL
    '12123': 'taylor2024', #Taylor County, FL
    '12125': 'union2024', #Union County, FL
    '12127': 'volusia2024', #Volusia County, FL
    '12129': 'wakulla2024', #Wakulla County, FL
    '12131': 'walton2024', #Walton County, FL
    '12133': 'washington2024', #Washington County, FL
    '13001': 'appling2024', #Appling County, GA
    '13003': 'atkinson2024', #Atkinson County, GA
    '13005': 'bacon2024', #Bacon County, GA
    '13007': 'baker2024', #Baker County, GA
    '13009': 'baldwin2024', #Baldwin County, GA
    '13011': 'banks2024', #Banks County, GA
    '13013': 'barrow2024', #Barrow County, GA
    '13015': 'bartow2024', #Bartow County, GA
    '13017': 'ben hill2024', #Ben Hill County, GA
    '13019': 'berrien2024', #Berrien County, GA
    '13021': 'bibb2024', #Bibb County, GA
    '13023': 'bleckley2024', #Bleckley County, GA
    '13025': 'brantley2024', #Brantley County, GA
    '13027': 'brooks2024', #Brooks County, GA
    '13029': 'bryan2024', #Bryan County, GA
    '13031': 'bulloch2024', #Bulloch County, GA
    '13033': 'burke2024', #Burke County, GA
    '13035': 'butts2024', #Butts County, GA
    '13037': 'calhoun2024', #Calhoun County, GA
    '13039': 'camden2024', #Camden County, GA
    '13043': 'candler2024', #Candler County, GA
    '13045': 'carroll2024', #Carroll County, GA
    '13047': 'catoosa2024', #Catoosa County, GA
    '13049': 'charlton2024', #Charlton County, GA
    '13051': 'chatham2024', #Chatham County, GA
    '13053': 'chattahoochee2024', #Chattahoochee County, GA
    '13055': 'chattooga2024', #Chattooga County, GA
    '13057': 'cherokee2024', #Cherokee County, GA
    '13059': 'clarke2024', #Clarke County, GA
    '13061': 'clay2024', #Clay County, GA
    '13063': 'clayton2024', #Clayton County, GA
    '13065': 'clinch2024', #Clinch County, GA
    '13067': 'cobb2024', #Cobb County, GA
    '13069': 'coffee2024', #Coffee County, GA
    '13071': 'colquitt2024', #Colquitt County, GA
    '13073': 'columbia2024', #Columbia County, GA
    '13075': 'cook2024', #Cook County, GA
    '13077': 'coweta2024', #Coweta County, GA
    '13079': 'crawford2024', #Crawford County, GA
    '13081': 'crisp2024', #Crisp County, GA
    '13083': 'dade2024', #Dade County, GA
    '13085': 'dawson2024', #Dawson County, GA
    '13087': 'decatur2024', #Decatur County, GA
    '13089': 'dekalb2024', #DeKalb County, GA
    '13091': 'dodge2024', #Dodge County, GA
    '13093': 'dooly2024', #Dooly County, GA
    '13095': 'dougherty2024', #Dougherty County, GA
    '13097': 'douglas2024', #Douglas County, GA
    '13099': 'early2024', #Early County, GA
    '13101': 'echols2024', #Echols County, GA
    '13103': 'effingham2024', #Effingham County, GA
    '13105': 'elbert2024', #Elbert County, GA
    '13107': 'emanuel2024', #Emanuel County, GA
    '13109': 'evans2024', #Evans County, GA
    '13111': 'fannin2024', #Fannin County, GA
    '13113': 'fayette2024', #Fayette County, GA
    '13115': 'floyd2024', #Floyd County, GA
    '13117': 'forsyth2024', #Forsyth County, GA
    '13119': 'franklin2024', #Franklin County, GA
    '13121': 'fulton2024', #Fulton County, GA
    '13123': 'gilmer2024', #Gilmer County, GA
    '13125': 'glascock2024', #Glascock County, GA
    '13127': 'glynn2024', #Glynn County, GA
    '13129': 'gordon2024', #Gordon County, GA
    '13131': 'grady2024', #Grady County, GA
    '13133': 'greene2024', #Greene County, GA
    '13135': 'gwinnett2024', #Gwinnett County, GA
    '13137': 'habersham2024', #Habersham County, GA
    '13139': 'hall2024', #Hall County, GA
    '13141': 'hancock2024', #Hancock County, GA
    '13143': 'haralson2024', #Haralson County, GA
    '13145': 'harris2024', #Harris County, GA
    '13147': 'hart2024', #Hart County, GA
    '13149': 'heard2024', #Heard County, GA
    '13151': 'henry2024', #Henry County, GA
    '13153': 'houston2024', #Houston County, GA
    '13155': 'irwin2024', #Irwin County, GA
    '13157': 'jackson2024', #Jackson County, GA
    '13159': 'jasper2024', #Jasper County, GA
    '13161': 'jeff davis2024', #Jeff Davis County, GA
    '13163': 'jefferson2024', #Jefferson County, GA
    '13165': 'jenkins2024', #Jenkins County, GA
    '13167': 'johnson2024', #Johnson County, GA
    '13169': 'jones2024', #Jones County, GA
    '13171': 'lamar2024', #Lamar County, GA
    '13173': 'lanier2024', #Lanier County, GA
    '13175': 'laurens2024', #Laurens County, GA
    '13177': 'lee2024', #Lee County, GA
    '13179': 'liberty2024', #Liberty County, GA
    '13181': 'lincoln2024', #Lincoln County, GA
    '13183': 'long2024', #Long County, GA
    '13185': 'lowndes2024', #Lowndes County, GA
    '13187': 'lumpkin2024', #Lumpkin County, GA
    '13189': 'mcduffie2024', #McDuffie County, GA
    '13191': 'mcintosh2024', #McIntosh County, GA
    '13193': 'macon2024', #Macon County, GA
    '13195': 'madison2024', #Madison County, GA
    '13197': 'marion2024', #Marion County, GA
    '13199': 'meriwether2024', #Meriwether County, GA
    '13201': 'miller2024', #Miller County, GA
    '13205': 'mitchell2024', #Mitchell County, GA
    '13207': 'monroe2024', #Monroe County, GA
    '13209': 'montgomery2024', #Montgomery County, GA
    '13211': 'morgan2024', #Morgan County, GA
    '13213': 'murray2024', #Murray County, GA
    '13215': 'muscogee2024', #Muscogee County, GA
    '13217': 'newton2024', #Newton County, GA
    '13219': 'oconee2024', #Oconee County, GA
    '13221': 'oglethorpe2024', #Oglethorpe County, GA
    '13223': 'paulding2024', #Paulding County, GA
    '13225': 'peach2024', #Peach County, GA
    '13227': 'pickens2024', #Pickens County, GA
    '13229': 'pierce2024', #Pierce County, GA
    '13231': 'pike2024', #Pike County, GA
    '13233': 'polk2024', #Polk County, GA
    '13235': 'pulaski2024', #Pulaski County, GA
    '13237': 'putnam2024', #Putnam County, GA
    '13239': 'quitman2024', #Quitman County, GA
    '13241': 'rabun2024', #Rabun County, GA
    '13243': 'randolph2024', #Randolph County, GA
    '13245': 'richmond2024', #Richmond County, GA
    '13247': 'rockdale2024', #Rockdale County, GA
    '13249': 'schley2024', #Schley County, GA
    '13251': 'screven2024', #Screven County, GA
    '13253': 'seminole2024', #Seminole County, GA
    '13255': 'spalding2024', #Spalding County, GA
    '13257': 'stephens2024', #Stephens County, GA
    '13259': 'stewart2024', #Stewart County, GA
    '13261': 'sumter2024', #Sumter County, GA
    '13263': 'talbot2024', #Talbot County, GA
    '13265': 'taliaferro2024', #Taliaferro County, GA
    '13267': 'tattnall2024', #Tattnall County, GA
    '13269': 'taylor2024', #Taylor County, GA
    '13271': 'telfair2024', #Telfair County, GA
    '13273': 'terrell2024', #Terrell County, GA
    '13275': 'thomas2024', #Thomas County, GA
    '13277': 'tift2024', #Tift County, GA
    '13279': 'toombs2024', #Toombs County, GA
    '13281': 'towns2024', #Towns County, GA
    '13283': 'treutlen2024', #Treutlen County, GA
    '13285': 'troup2024', #Troup County, GA
    '13287': 'turner2024', #Turner County, GA
    '13289': 'twiggs2024', #Twiggs County, GA
    '13291': 'union2024', #Union County, GA
    '13293': 'upson2024', #Upson County, GA
    '13295': 'walker2024', #Walker County, GA
    '13297': 'walton2024', #Walton County, GA
    '13299': 'ware2024', #Ware County, GA
    '13301': 'warren2024', #Warren County, GA
    '13303': 'washington2024', #Washington County, GA
    '13305': 'wayne2024', #Wayne County, GA
    '13307': 'webster2024', #Webster County, GA
    '13309': 'wheeler2024', #Wheeler County, GA
    '13311': 'white2024', #White County, GA
    '13313': 'whitfield2024', #Whitfield County, GA
    '13315': 'wilcox2024', #Wilcox County, GA
    '13317': 'wilkes2024', #Wilkes County, GA
    '13319': 'wilkinson2024', #Wilkinson County, GA
    '13321': 'worth2024', #Worth County, GA
    '15001': 'hawaii2024', #Hawaii County, HI
    '15003': 'honolulu2024', #Honolulu County, HI
    '15005': 'kalawao2024', #Kalawao County, HI
    '15007': 'kauai2024', #Kauai County, HI
    '15009': 'maui2024', #Maui County, HI
    '16001': 'ada2024', #Ada County, ID
    '16003': 'adams2024', #Adams County, ID
    '16005': 'bannock2024', #Bannock County, ID
    '16007': 'bear lake2024', #Bear Lake County, ID
    '16009': 'benewah2024', #Benewah County, ID
    '16011': 'bingham2024', #Bingham County, ID
    '16013': 'blaine2024', #Blaine County, ID
    '16015': 'boise2024', #Boise County, ID
    '16017': 'bonner2024', #Bonner County, ID
    '16019': 'bonneville2024', #Bonneville County, ID
    '16021': 'boundary2024', #Boundary County, ID
    '16023': 'butte2024', #Butte County, ID
    '16025': 'camas2024', #Camas County, ID
    '16027': 'canyon2024', #Canyon County, ID
    '16029': 'caribou2024', #Caribou County, ID
    '16031': 'cassia2024', #Cassia County, ID
    '16033': 'clark2024', #Clark County, ID
    '16035': 'clearwater2024', #Clearwater County, ID
    '16037': 'custer2024', #Custer County, ID
    '16039': 'elmore2024', #Elmore County, ID
    '16041': 'franklin2024', #Franklin County, ID
    '16043': 'fremont2024', #Fremont County, ID
    '16045': 'gem2024', #Gem County, ID
    '16047': 'gooding2024', #Gooding County, ID
    '16049': 'idaho2024', #Idaho County, ID
    '16051': 'jefferson2024', #Jefferson County, ID
    '16053': 'jerome2024', #Jerome County, ID
    '16055': 'kootenai2024', #Kootenai County, ID
    '16057': 'latah2024', #Latah County, ID
    '16059': 'lemhi2024', #Lemhi County, ID
    '16061': 'lewis2024', #Lewis County, ID
    '16063': 'lincoln2024', #Lincoln County, ID
    '16065': 'madison2024', #Madison County, ID
    '16067': 'minidoka2024', #Minidoka County, ID
    '16069': 'nez perce2024', #Nez Perce County, ID
    '16071': 'oneida2024', #Oneida County, ID
    '16073': 'owyhee2024', #Owyhee County, ID
    '16075': 'payette2024', #Payette County, ID
    '16077': 'power2024', #Power County, ID
    '16079': 'shoshone2024', #Shoshone County, ID
    '16081': 'teton2024', #Teton County, ID
    '16083': 'twin falls2024', #Twin Falls County, ID
    '16085': 'valley2024', #Valley County, ID
    '16087': 'washington2024', #Washington County, ID
    '17001': 'adams2024', #Adams County, IL
    '17003': 'alexander2024', #Alexander County, IL
    '17005': 'bond2024', #Bond County, IL
    '17007': 'boone2024', #Boone County, IL
    '17009': 'brown2024', #Brown County, IL
    '17011': 'bureau2024', #Bureau County, IL
    '17013': 'calhoun2024', #Calhoun County, IL
    '17015': 'carroll2024', #Carroll County, IL
    '17017': 'cass2024', #Cass County, IL
    '17019': 'champaign2024', #Champaign County, IL
    '17021': 'christian2024', #Christian County, IL
    '17023': 'clark2024', #Clark County, IL
    '17025': 'clay2024', #Clay County, IL
    '17027': 'clinton2024', #Clinton County, IL
    '17029': 'coles2024', #Coles County, IL
    '17031': 'cook2024', #Cook County, IL
    '17033': 'crawford2024', #Crawford County, IL
    '17035': 'cumberland2024', #Cumberland County, IL
    '17037': 'dekalb2024', #DeKalb County, IL
    '17039': 'de witt2024', #De Witt County, IL
    '17041': 'douglas2024', #Douglas County, IL
    '17043': 'dupage2024', #DuPage County, IL
    '17045': 'edgar2024', #Edgar County, IL
    '17047': 'edwards2024', #Edwards County, IL
    '17049': 'effingham2024', #Effingham County, IL
    '17051': 'fayette2024', #Fayette County, IL
    '17053': 'ford2024', #Ford County, IL
    '17055': 'franklin2024', #Franklin County, IL
    '17057': 'fulton2024', #Fulton County, IL
    '17059': 'gallatin2024', #Gallatin County, IL
    '17061': 'greene2024', #Greene County, IL
    '17063': 'grundy2024', #Grundy County, IL
    '17065': 'hamilton2024', #Hamilton County, IL
    '17067': 'hancock2024', #Hancock County, IL
    '17069': 'hardin2024', #Hardin County, IL
    '17071': 'henderson2024', #Henderson County, IL
    '17073': 'henry2024', #Henry County, IL
    '17075': 'iroquois2024', #Iroquois County, IL
    '17077': 'jackson2024', #Jackson County, IL
    '17079': 'jasper2024', #Jasper County, IL
    '17081': 'jefferson2024', #Jefferson County, IL
    '17083': 'jersey2024', #Jersey County, IL
    '17085': 'jo daviess2024', #Jo Daviess County, IL
    '17087': 'johnson2024', #Johnson County, IL
    '17089': 'kane2024', #Kane County, IL
    '17091': 'kankakee2024', #Kankakee County, IL
    '17093': 'kendall2024', #Kendall County, IL
    '17095': 'knox2024', #Knox County, IL
    '17097': 'lake2024', #Lake County, IL
    '17099': 'lasalle2024', #LaSalle County, IL
    '17101': 'lawrence2024', #Lawrence County, IL
    '17103': 'lee2024', #Lee County, IL
    '17105': 'livingston2024', #Livingston County, IL
    '17107': 'logan2024', #Logan County, IL
    '17109': 'mcdonough2024', #McDonough County, IL
    '17111': 'mchenry2024', #McHenry County, IL
    '17113': 'mclean2024', #McLean County, IL
    '17115': 'macon2024', #Macon County, IL
    '17117': 'macoupin2024', #Macoupin County, IL
    '17119': 'madison2024', #Madison County, IL
    '17121': 'marion2024', #Marion County, IL
    '17123': 'marshall2024', #Marshall County, IL
    '17125': 'mason2024', #Mason County, IL
    '17127': 'massac2024', #Massac County, IL
    '17129': 'menard2024', #Menard County, IL
    '17131': 'mercer2024', #Mercer County, IL
    '17133': 'monroe2024', #Monroe County, IL
    '17135': 'montgomery2024', #Montgomery County, IL
    '17137': 'morgan2024', #Morgan County, IL
    '17139': 'moultrie2024', #Moultrie County, IL
    '17141': 'ogle2024', #Ogle County, IL
    '17143': 'peoria2024', #Peoria County, IL
    '17145': 'perry2024', #Perry County, IL
    '17147': 'piatt2024', #Piatt County, IL
    '17149': 'pike2024', #Pike County, IL
    '17151': 'pope2024', #Pope County, IL
    '17153': 'pulaski2024', #Pulaski County, IL
    '17155': 'putnam2024', #Putnam County, IL
    '17157': 'randolph2024', #Randolph County, IL
    '17159': 'richland2024', #Richland County, IL
    '17161': 'rock island2024', #Rock Island County, IL
    '17163': 'st. clair2024', #St. Clair County, IL
    '17165': 'saline2024', #Saline County, IL
    '17167': 'sangamon2024', #Sangamon County, IL
    '17169': 'schuyler2024', #Schuyler County, IL
    '17171': 'scott2024', #Scott County, IL
    '17173': 'shelby2024', #Shelby County, IL
    '17175': 'stark2024', #Stark County, IL
    '17177': 'stephenson2024', #Stephenson County, IL
    '17179': 'tazewell2024', #Tazewell County, IL
    '17181': 'union2024', #Union County, IL
    '17183': 'vermilion2024', #Vermilion County, IL
    '17185': 'wabash2024', #Wabash County, IL
    '17187': 'warren2024', #Warren County, IL
    '17189': 'washington2024', #Washington County, IL
    '17191': 'wayne2024', #Wayne County, IL
    '17193': 'white2024', #White County, IL
    '17195': 'whiteside2024', #Whiteside County, IL
    '17197': 'will2024', #Will County, IL
    '17199': 'williamson2024', #Williamson County, IL
    '17201': 'winnebago2024', #Winnebago County, IL
    '17203': 'woodford2024', #Woodford County, IL
    '18001': 'adams2024', #Adams County, 
    '18003': 'allen2024', #Allen County, 
    '18005': 'bartholomew2024', #Bartholomew County, 
    '18007': 'benton2024', #Benton County, 
    '18009': 'blackford2024', #Blackford County, 
    '18011': 'boone2024', #Boone County, 
    '18013': 'brown2024', #Brown County, 
    '18015': 'carroll2024', #Carroll County, 
    '18017': 'cass2024', #Cass County, 
    '18019': 'clark2024', #Clark County, 
    '18021': 'clay2024', #Clay County, 
    '18023': 'clinton2024', #Clinton County, 
    '18025': 'crawford2024', #Crawford County, 
    '18027': 'daviess2024', #Daviess County, 
    '18029': 'dearborn2024', #Dearborn County, 
    '18031': 'decatur2024', #Decatur County, 
    '18033': 'dekalb2024', #DeKalb County, 
    '18035': 'delaware2024', #Delaware County, 
    '18037': 'dubois2024', #Dubois County, 
    '18039': 'elkhart2024', #Elkhart County, 
    '18041': 'fayette2024', #Fayette County, 
    '18043': 'floyd2024', #Floyd County, 
    '18045': 'fountain2024', #Fountain County, 
    '18047': 'franklin2024', #Franklin County, 
    '18049': 'fulton2024', #Fulton County, 
    '18051': 'gibson2024', #Gibson County, 
    '18053': 'grant2024', #Grant County, 
    '18055': 'greene2024', #Greene County, 
    '18057': 'hamilton2024', #Hamilton County, 
    '18059': 'hancock2024', #Hancock County, 
    '18061': 'harrison2024', #Harrison County, 
    '18063': 'hendricks2024', #Hendricks County, 
    '18065': 'henry2024', #Henry County, 
    '18067': 'howard2024', #Howard County, 
    '18069': 'huntington2024', #Huntington County, 
    '18071': 'jackson2024', #Jackson County, 
    '18073': 'jasper2024', #Jasper County, 
    '18075': 'jay2024', #Jay County, 
    '18077': 'jefferson2024', #Jefferson County, 
    '18079': 'jennings2024', #Jennings County, 
    '18081': 'johnson2024', #Johnson County, 
    '18083': 'knox2024', #Knox County, 
    '18085': 'kosciusko2024', #Kosciusko County, 
    '18087': 'lagrange2024', #LaGrange County, 
    '18089': 'lake2024', #Lake County, 
    '18091': 'laporte2024', #LaPorte County, 
    '18093': 'lawrence2024', #Lawrence County, 
    '18095': 'madison2024', #Madison County, 
    '18097': 'marion2024', #Marion County, 
    '18099': 'marshall2024', #Marshall County, 
    '18101': 'martin2024', #Martin County, 
    '18103': 'miami2024', #Miami County, 
    '18105': 'monroe2024', #Monroe County, 
    '18107': 'montgomery2024', #Montgomery County, 
    '18109': 'morgan2024', #Morgan County, 
    '18111': 'newton2024', #Newton County, 
    '18113': 'noble2024', #Noble County, 
    '18115': 'ohio2024', #Ohio County, 
    '18117': 'orange2024', #Orange County, 
    '18119': 'owen2024', #Owen County, 
    '18121': 'parke2024', #Parke County, 
    '18123': 'perry2024', #Perry County, 
    '18125': 'pike2024', #Pike County, 
    '18127': 'porter2024', #Porter County, 
    '18129': 'posey2024', #Posey County, 
    '18131': 'pulaski2024', #Pulaski County, 
    '18133': 'putnam2024', #Putnam County, 
    '18135': 'randolph2024', #Randolph County, 
    '18137': 'ripley2024', #Ripley County, 
    '18139': 'rush2024', #Rush County, 
    '18141': 'st. joseph2024', #St. Joseph County, 
    '18143': 'scott2024', #Scott County, 
    '18145': 'shelby2024', #Shelby County, 
    '18147': 'spencer2024', #Spencer County, 
    '18149': 'starke2024', #Starke County, 
    '18151': 'steuben2024', #Steuben County, 
    '18153': 'sullivan2024', #Sullivan County, 
    '18155': 'switzerland2024', #Switzerland County, 
    '18157': 'tippecanoe2024', #Tippecanoe County, 
    '18159': 'tipton2024', #Tipton County, 
    '18161': 'union2024', #Union County, 
    '18163': 'vanderburgh2024', #Vanderburgh County, 
    '18165': 'vermillion2024', #Vermillion County, 
    '18167': 'vigo2024', #Vigo County, 
    '18169': 'wabash2024', #Wabash County, 
    '18171': 'warren2024', #Warren County, 
    '18173': 'warrick2024', #Warrick County, 
    '18175': 'washington2024', #Washington County, 
    '18177': 'wayne2024', #Wayne County, 
    '18179': 'wells2024', #Wells County, 
    '18181': 'white2024', #White County, 
    '18183': 'whitley2024', #Whitley County, 
    '19001': 'adair2024', #Adair County, IA
    '19003': 'adams2024', #Adams County, IA
    '19005': 'allamakee2024', #Allamakee County, IA
    '19007': 'appanoose2024', #Appanoose County, IA
    '19009': 'audubon2024', #Audubon County, IA
    '19011': 'benton2024', #Benton County, IA
    '19013': 'black hawk2024', #Black Hawk County, IA
    '19015': 'boone2024', #Boone County, IA
    '19017': 'bremer2024', #Bremer County, IA
    '19019': 'buchanan2024', #Buchanan County, IA
    '19021': 'buena vista2024', #Buena Vista County, IA
    '19023': 'butler2024', #Butler County, IA
    '19025': 'calhoun2024', #Calhoun County, IA
    '19027': 'carroll2024', #Carroll County, IA
    '19029': 'cass2024', #Cass County, IA
    '19031': 'cedar2024', #Cedar County, IA
    '19033': 'cerro gordo2024', #Cerro Gordo County, IA
    '19035': 'cherokee2024', #Cherokee County, IA
    '19037': 'chickasaw2024', #Chickasaw County, IA
    '19039': 'clarke2024', #Clarke County, IA
    '19041': 'clay2024', #Clay County, IA
    '19043': 'clayton2024', #Clayton County, IA
    '19045': 'clinton2024', #Clinton County, IA
    '19047': 'crawford2024', #Crawford County, IA
    '19049': 'dallas2024', #Dallas County, IA
    '19051': 'davis2024', #Davis County, IA
    '19053': 'decatur2024', #Decatur County, IA
    '19055': 'delaware2024', #Delaware County, IA
    '19057': 'des moines2024', #Des Moines County, IA
    '19059': 'dickinson2024', #Dickinson County, IA
    '19061': 'dubuque2024', #Dubuque County, IA
    '19063': 'emmet2024', #Emmet County, IA
    '19065': 'fayette2024', #Fayette County, IA
    '19067': 'floyd2024', #Floyd County, IA
    '19069': 'franklin2024', #Franklin County, IA
    '19071': 'fremont2024', #Fremont County, IA
    '19073': 'greene2024', #Greene County, IA
    '19075': 'grundy2024', #Grundy County, IA
    '19077': 'guthrie2024', #Guthrie County, IA
    '19079': 'hamilton2024', #Hamilton County, IA
    '19081': 'hancock2024', #Hancock County, IA
    '19083': 'hardin2024', #Hardin County, IA
    '19085': 'harrison2024', #Harrison County, IA
    '19087': 'henry2024', #Henry County, IA
    '19089': 'howard2024', #Howard County, IA
    '19091': 'humboldt2024', #Humboldt County, IA
    '19093': 'ida2024', #Ida County, IA
    '19095': 'iowa2024', #Iowa County, IA
    '19097': 'jackson2024', #Jackson County, IA
    '19099': 'jasper2024', #Jasper County, IA
    '19101': 'jefferson2024', #Jefferson County, IA
    '19103': 'johnson2024', #Johnson County, IA
    '19105': 'jones2024', #Jones County, IA
    '19107': 'keokuk2024', #Keokuk County, IA
    '19109': 'kossuth2024', #Kossuth County, IA
    '19111': 'lee2024', #Lee County, IA
    '19113': 'linn2024', #Linn County, IA
    '19115': 'louisa2024', #Louisa County, IA
    '19117': 'lucas2024', #Lucas County, IA
    '19119': 'lyon2024', #Lyon County, IA
    '19121': 'madison2024', #Madison County, IA
    '19123': 'mahaska2024', #Mahaska County, IA
    '19125': 'marion2024', #Marion County, IA
    '19127': 'marshall2024', #Marshall County, IA
    '19129': 'mills2024', #Mills County, IA
    '19131': 'mitchell2024', #Mitchell County, IA
    '19133': 'monona2024', #Monona County, IA
    '19135': 'monroe2024', #Monroe County, IA
    '19137': 'montgomery2024', #Montgomery County, IA
    '19139': 'muscatine2024', #Muscatine County, IA
    '19141': "o'brien2024", #O'Brien County, IA
    '19143': 'osceola2024', #Osceola County, IA
    '19145': 'page2024', #Page County, IA
    '19147': 'palo alto2024', #Palo Alto County, IA
    '19149': 'plymouth2024', #Plymouth County, IA
    '19151': 'pocahontas2024', #Pocahontas County, IA
    '19153': 'polk2024', #Polk County, IA
    '19155': 'pottawattamie2024', #Pottawattamie County, IA
    '19157': 'poweshiek2024', #Poweshiek County, IA
    '19159': 'ringgold2024', #Ringgold County, IA
    '19161': 'sac2024', #Sac County, IA
    '19163': 'scott2024', #Scott County, IA
    '19165': 'shelby2024', #Shelby County, IA
    '19167': 'sioux2024', #Sioux County, IA
    '19169': 'story2024', #Story County, IA
    '19171': 'tama2024', #Tama County, IA
    '19173': 'taylor2024', #Taylor County, IA
    '19175': 'union2024', #Union County, IA
    '19177': 'van buren2024', #Van Buren County, IA
    '19179': 'wapello2024', #Wapello County, IA
    '19181': 'warren2024', #Warren County, IA
    '19183': 'washington2024', #Washington County, IA
    '19185': 'wayne2024', #Wayne County, IA
    '19187': 'webster2024', #Webster County, IA
    '19189': 'winnebago2024', #Winnebago County, IA
    '19191': 'winneshiek2024', #Winneshiek County, IA
    '19193': 'woodbury2024', #Woodbury County, IA
    '19195': 'worth2024', #Worth County, IA
    '19197': 'wright2024', #Wright County, IA
    '20001': 'allen2024', #Allen County, KS
    '20003': 'anderson2024', #Anderson County, KS
    '20005': 'atchison2024', #Atchison County, KS
    '20007': 'barber2024', #Barber County, KS
    '20009': 'barton2024', #Barton County, KS
    '20011': 'bourbon2024', #Bourbon County, KS
    '20013': 'brown2024', #Brown County, KS
    '20015': 'butler2024', #Butler County, KS
    '20017': 'chase2024', #Chase County, KS
    '20019': 'chautauqua2024', #Chautauqua County, KS
    '20021': 'cherokee2024', #Cherokee County, KS
    '20023': 'cheyenne2024', #Cheyenne County, KS
    '20025': 'clark2024', #Clark County, KS
    '20027': 'clay2024', #Clay County, KS
    '20029': 'cloud2024', #Cloud County, KS
    '20031': 'coffey2024', #Coffey County, KS
    '20033': 'comanche2024', #Comanche County, KS
    '20035': 'cowley2024', #Cowley County, KS
    '20037': 'crawford2024', #Crawford County, KS
    '20039': 'decatur2024', #Decatur County, KS
    '20041': 'dickinson2024', #Dickinson County, KS
    '20043': 'doniphan2024', #Doniphan County, KS
    '20045': 'douglas2024', #Douglas County, KS
    '20047': 'edwards2024', #Edwards County, KS
    '20049': 'elk2024', #Elk County, KS
    '20051': 'ellis2024', #Ellis County, KS
    '20053': 'ellsworth2024', #Ellsworth County, KS
    '20055': 'finney2024', #Finney County, KS
    '20057': 'ford2024', #Ford County, KS
    '20059': 'franklin2024', #Franklin County, KS
    '20061': 'geary2024', #Geary County, KS
    '20063': 'gove2024', #Gove County, KS
    '20065': 'graham2024', #Graham County, KS
    '20067': 'grant2024', #Grant County, KS
    '20069': 'gray2024', #Gray County, KS
    '20071': 'greeley2024', #Greeley County, KS
    '20073': 'greenwood2024', #Greenwood County, KS
    '20075': 'hamilton2024', #Hamilton County, KS
    '20077': 'harper2024', #Harper County, KS
    '20079': 'harvey2024', #Harvey County, KS
    '20081': 'haskell2024', #Haskell County, KS
    '20083': 'hodgeman2024', #Hodgeman County, KS
    '20085': 'jackson2024', #Jackson County, KS
    '20087': 'jefferson2024', #Jefferson County, KS
    '20089': 'jewell2024', #Jewell County, KS
    '20091': 'johnson2024', #Johnson County, KS
    '20093': 'kearny2024', #Kearny County, KS
    '20095': 'kingman2024', #Kingman County, KS
    '20097': 'kiowa2024', #Kiowa County, KS
    '20099': 'labette2024', #Labette County, KS
    '20101': 'lane2024', #Lane County, KS
    '20103': 'leavenworth2024', #Leavenworth County, KS
    '20105': 'lincoln2024', #Lincoln County, KS
    '20107': 'linn2024', #Linn County, KS
    '20109': 'logan2024', #Logan County, KS
    '20111': 'lyon2024', #Lyon County, KS
    '20113': 'mcpherson2024', #McPherson County, KS
    '20115': 'marion2024', #Marion County, KS
    '20117': 'marshall2024', #Marshall County, KS
    '20119': 'meade2024', #Meade County, KS
    '20121': 'miami2024', #Miami County, KS
    '20123': 'mitchell2024', #Mitchell County, KS
    '20125': 'montgomery2024', #Montgomery County, KS
    '20127': 'morris2024', #Morris County, KS
    '20129': 'morton2024', #Morton County, KS
    '20131': 'nemaha2024', #Nemaha County, KS
    '20133': 'neosho2024', #Neosho County, KS
    '20135': 'ness2024', #Ness County, KS
    '20137': 'norton2024', #Norton County, KS
    '20139': 'osage2024', #Osage County, KS
    '20141': 'osborne2024', #Osborne County, KS
    '20143': 'ottawa2024', #Ottawa County, KS
    '20145': 'pawnee2024', #Pawnee County, KS
    '20147': 'phillips2024', #Phillips County, KS
    '20149': 'pottawatomie2024', #Pottawatomie County, KS
    '20151': 'pratt2024', #Pratt County, KS
    '20153': 'rawlins2024', #Rawlins County, KS
    '20155': 'reno2024', #Reno County, KS
    '20157': 'republic2024', #Republic County, KS
    '20159': 'rice2024', #Rice County, KS
    '20161': 'riley2024', #Riley County, KS
    '20163': 'rooks2024', #Rooks County, KS
    '20165': 'rush2024', #Rush County, KS
    '20167': 'russell2024', #Russell County, KS
    '20169': 'saline2024', #Saline County, KS
    '20171': 'scott2024', #Scott County, KS
    '20173': 'sedgwick2024', #Sedgwick County, KS
    '20175': 'seward2024', #Seward County, KS
    '20177': 'shawnee2024', #Shawnee County, KS
    '20179': 'sheridan2024', #Sheridan County, KS
    '20181': 'sherman2024', #Sherman County, KS
    '20183': 'smith2024', #Smith County, KS
    '20185': 'stafford2024', #Stafford County, KS
    '20187': 'stanton2024', #Stanton County, KS
    '20189': 'stevens2024', #Stevens County, KS
    '20191': 'sumner2024', #Sumner County, KS
    '20193': 'thomas2024', #Thomas County, KS
    '20195': 'trego2024', #Trego County, KS
    '20197': 'wabaunsee2024', #Wabaunsee County, KS
    '20199': 'wallace2024', #Wallace County, KS
    '20201': 'washington2024', #Washington County, KS
    '20203': 'wichita2024', #Wichita County, KS
    '20205': 'wilson2024', #Wilson County, KS
    '20207': 'woodson2024', #Woodson County, KS
    '20209': 'wyandotte2024', #Wyandotte County, KS
    '21001': 'adair2024', #Adair County, KY
    '21003': 'allen2024', #Allen County, KY
    '21005': 'anderson2024', #Anderson County, KY
    '21007': 'ballard2024', #Ballard County, KY
    '21009': 'barren2024', #Barren County, KY
    '21011': 'bath2024', #Bath County, KY
    '21013': 'bell2024', #Bell County, KY
    '21015': 'boone2024', #Boone County, KY
    '21017': 'bourbon2024', #Bourbon County, KY
    '21019': 'boyd2024', #Boyd County, KY
    '21021': 'boyle2024', #Boyle County, KY
    '21023': 'bracken2024', #Bracken County, KY
    '21025': 'breathitt2024', #Breathitt County, KY
    '21027': 'breckinridge2024', #Breckinridge County, KY
    '21029': 'bullitt2024', #Bullitt County, KY
    '21031': 'butler2024', #Butler County, KY
    '21033': 'caldwell2024', #Caldwell County, KY
    '21035': 'calloway2024', #Calloway County, KY
    '21037': 'campbell2024', #Campbell County, KY
    '21039': 'carlisle2024', #Carlisle County, KY
    '21041': 'carroll2024', #Carroll County, KY
    '21043': 'carter2024', #Carter County, KY
    '21045': 'casey2024', #Casey County, KY
    '21047': 'christian2024', #Christian County, KY
    '21049': 'clark2024', #Clark County, KY
    '21051': 'clay2024', #Clay County, KY
    '21053': 'clinton2024', #Clinton County, KY
    '21055': 'crittenden2024', #Crittenden County, KY
    '21057': 'cumberland2024', #Cumberland County, KY
    '21059': 'daviess2024', #Daviess County, KY
    '21061': 'edmonson2024', #Edmonson County, KY
    '21063': 'elliott2024', #Elliott County, KY
    '21065': 'estill2024', #Estill County, KY
    '21067': 'fayette2024', #Fayette County, KY
    '21069': 'fleming2024', #Fleming County, KY
    '21071': 'floyd2024', #Floyd County, KY
    '21073': 'franklin2024', #Franklin County, KY
    '21075': 'fulton2024', #Fulton County, KY
    '21077': 'gallatin2024', #Gallatin County, KY
    '21079': 'garrard2024', #Garrard County, KY
    '21081': 'grant2024', #Grant County, KY
    '21083': 'graves2024', #Graves County, KY
    '21085': 'grayson2024', #Grayson County, KY
    '21087': 'green2024', #Green County, KY
    '21089': 'greenup2024', #Greenup County, KY
    '21091': 'hancock2024', #Hancock County, KY
    '21093': 'hardin2024', #Hardin County, KY
    '21095': 'harlan2024', #Harlan County, KY
    '21097': 'harrison2024', #Harrison County, KY
    '21099': 'hart2024', #Hart County, KY
    '21101': 'henderson2024', #Henderson County, KY
    '21103': 'henry2024', #Henry County, KY
    '21105': 'hickman2024', #Hickman County, KY
    '21107': 'hopkins2024', #Hopkins County, KY
    '21109': 'jackson2024', #Jackson County, KY
    '21111': 'jefferson2024', #Jefferson County, KY
    '21113': 'jessamine2024', #Jessamine County, KY
    '21115': 'johnson2024', #Johnson County, KY
    '21117': 'kenton2024', #Kenton County, KY
    '21119': 'knott2024', #Knott County, KY
    '21121': 'knox2024', #Knox County, KY
    '21123': 'larue2024', #Larue County, KY
    '21125': 'laurel2024', #Laurel County, KY
    '21127': 'lawrence2024', #Lawrence County, KY
    '21129': 'lee2024', #Lee County, KY
    '21131': 'leslie2024', #Leslie County, KY
    '21133': 'letcher2024', #Letcher County, KY
    '21135': 'lewis2024', #Lewis County, KY
    '21137': 'lincoln2024', #Lincoln County, KY
    '21139': 'livingston2024', #Livingston County, KY
    '21141': 'logan2024', #Logan County, KY
    '21143': 'lyon2024', #Lyon County, KY
    '21145': 'mccracken2024', #McCracken County, KY
    '21147': 'mccreary2024', #McCreary County, KY
    '21149': 'mclean2024', #McLean County, KY
    '21151': 'madison2024', #Madison County, KY
    '21153': 'magoffin2024', #Magoffin County, KY
    '21155': 'marion2024', #Marion County, KY
    '21157': 'marshall2024', #Marshall County, KY
    '21159': 'martin2024', #Martin County, KY
    '21161': 'mason2024', #Mason County, KY
    '21163': 'meade2024', #Meade County, KY
    '21165': 'menifee2024', #Menifee County, KY
    '21167': 'mercer2024', #Mercer County, KY
    '21169': 'metcalfe2024', #Metcalfe County, KY
    '21171': 'monroe2024', #Monroe County, KY
    '21173': 'montgomery2024', #Montgomery County, KY
    '21175': 'morgan2024', #Morgan County, KY
    '21177': 'muhlenberg2024', #Muhlenberg County, KY
    '21179': 'nelson2024', #Nelson County, KY
    '21181': 'nicholas2024', #Nicholas County, KY
    '21183': 'ohio2024', #Ohio County, KY
    '21185': 'oldham2024', #Oldham County, KY
    '21187': 'owen2024', #Owen County, KY
    '21189': 'owsley2024', #Owsley County, KY
    '21191': 'pendleton2024', #Pendleton County, KY
    '21193': 'perry2024', #Perry County, KY
    '21195': 'pike2024', #Pike County, KY
    '21197': 'powell2024', #Powell County, KY
    '21199': 'pulaski2024', #Pulaski County, KY
    '21201': 'robertson2024', #Robertson County, KY
    '21203': 'rockcastle2024', #Rockcastle County, KY
    '21205': 'rowan2024', #Rowan County, KY
    '21207': 'russell2024', #Russell County, KY
    '21209': 'scott2024', #Scott County, KY
    '21211': 'shelby2024', #Shelby County, KY
    '21213': 'simpson2024', #Simpson County, KY
    '21215': 'spencer2024', #Spencer County, KY
    '21217': 'taylor2024', #Taylor County, KY
    '21219': 'todd2024', #Todd County, KY
    '21221': 'trigg2024', #Trigg County, KY
    '21223': 'trimble2024', #Trimble County, KY
    '21225': 'union2024', #Union County, KY
    '21227': 'warren2024', #Warren County, KY
    '21229': 'washington2024', #Washington County, KY
    '21231': 'wayne2024', #Wayne County, KY
    '21233': 'webster2024', #Webster County, KY
    '21235': 'whitley2024', #Whitley County, KY
    '21237': 'wolfe2024', #Wolfe County, KY
    '21239': 'woodford2024', #Woodford County, KY
    '22001': 'acadia2024', #Acadia County, LA
    '22003': 'allen2024', #Allen County, LA
    '22005': 'ascension2024', #Ascension County, LA
    '22007': 'assumption2024', #Assumption County, LA
    '22009': 'avoyelles2024', #Avoyelles County, LA
    '22011': 'beauregard2024', #Beauregard County, LA
    '22013': 'bienville2024', #Bienville County, LA
    '22015': 'bossier2024', #Bossier County, LA
    '22017': 'caddo2024', #Caddo County, LA
    '22019': 'calcasieu2024', #Calcasieu County, LA
    '22021': 'caldwell2024', #Caldwell County, LA
    '22023': 'cameron2024', #Cameron County, LA
    '22025': 'catahoula2024', #Catahoula County, LA
    '22027': 'claiborne2024', #Claiborne County, LA
    '22029': 'concordia2024', #Concordia County, LA
    '22031': 'de soto2024', #De Soto County, LA
    '22033': 'east baton rouge2024', #East Baton Rouge County, LA
    '22035': 'east carroll2024', #East Carroll County, LA
    '22037': 'east feliciana2024', #East Feliciana County, LA
    '22039': 'evangeline2024', #Evangeline County, LA
    '22041': 'franklin2024', #Franklin County, LA
    '22043': 'grant2024', #Grant County, LA
    '22045': 'iberia2024', #Iberia County, LA
    '22047': 'iberville2024', #Iberville County, LA
    '22049': 'jackson2024', #Jackson County, LA
    '22051': 'jefferson2024', #Jefferson County, LA
    '22053': 'jefferson davis2024', #Jefferson Davis County, LA
    '22055': 'lafayette2024', #Lafayette County, LA
    '22057': 'lafourche2024', #Lafourche County, LA
    '22059': 'la salle2024', #La Salle County, LA
    '22061': 'lincoln2024', #Lincoln County, LA
    '22063': 'livingston2024', #Livingston County, LA
    '22065': 'madison2024', #Madison County, LA
    '22067': 'morehouse2024', #Morehouse County, LA
    '22069': 'natchitoches2024', #Natchitoches County, LA
    '22071': 'orleans2024', #Orleans County, LA
    '22073': 'ouachita2024', #Ouachita County, LA
    '22075': 'plaquemines2024', #Plaquemines County, LA
    '22077': 'pointe coupee2024', #Pointe Coupee County, LA
    '22079': 'rapides2024', #Rapides County, LA
    '22081': 'red river2024', #Red River County, LA
    '22083': 'richland2024', #Richland County, LA
    '22085': 'sabine2024', #Sabine County, LA
    '22087': 'st. bernard2024', #St. Bernard County, LA
    '22089': 'st. charles2024', #St. Charles County, LA
    '22091': 'st. helena2024', #St. Helena County, LA
    '22093': 'st. james2024', #St. James County, LA
    '22095': 'st. john the baptist2024', #St. John the Baptist County, LA
    '22097': 'st. landry2024', #St. Landry County, LA
    '22099': 'st. martin2024', #St. Martin County, LA
    '22101': 'st. mary2024', #St. Mary County, LA
    '22103': 'st. tammany2024', #St. Tammany County, LA
    '22105': 'tangipahoa2024', #Tangipahoa County, LA
    '22107': 'tensas2024', #Tensas County, LA
    '22109': 'terrebonne2024', #Terrebonne County, LA
    '22111': 'union2024', #Union County, LA
    '22113': 'vermilion2024', #Vermilion County, LA
    '22115': 'vernon2024', #Vernon County, LA
    '22117': 'washington2024', #Washington County, LA
    '22119': 'webster2024', #Webster County, LA
    '22121': 'west baton rouge2024', #West Baton Rouge County, LA
    '22123': 'west carroll2024', #West Carroll County, LA
    '22125': 'west feliciana2024', #West Feliciana County, LA
    '22127': 'winn2024', #Winn County, LA
    '23001': 'androscoggin2024', #Androscoggin County, ME
    '23003': 'aroostook2024', #Aroostook County, ME
    '23005': 'cumberland2024', #Cumberland County, ME
    '23007': 'franklin2024', #Franklin County, ME
    '23009': 'hancock2024', #Hancock County, ME
    '23011': 'kennebec2024', #Kennebec County, ME
    '23013': 'knox2024', #Knox County, ME
    '23015': 'lincoln2024', #Lincoln County, ME
    '23017': 'oxford2024', #Oxford County, ME
    '23019': 'penobscot2024', #Penobscot County, ME
    '23021': 'piscataquis2024', #Piscataquis County, ME
    '23023': 'sagadahoc2024', #Sagadahoc County, ME
    '23025': 'somerset2024', #Somerset County, ME
    '23027': 'waldo2024', #Waldo County, ME
    '23029': 'washington2024', #Washington County, ME
    '23031': 'york2024', #York County, ME
    '24001': 'allegany2024', #Allegany County, MD
    '24003': 'anne arundel2024', #Anne Arundel County, MD
    '24005': 'baltimore2024', #Baltimore County, MD
    '24009': 'calvert2024', #Calvert County, MD
    '24011': 'caroline2024', #Caroline County, MD
    '24013': 'carroll2024', #Carroll County, MD
    '24015': 'cecil2024', #Cecil County, MD
    '24017': 'charles2024', #Charles County, MD
    '24019': 'dorchester2024', #Dorchester County, MD
    '24021': 'frederick2024', #Frederick County, MD
    '24023': 'garrett2024', #Garrett County, MD
    '24025': 'harford2024', #Harford County, MD
    '24027': 'howard2024', #Howard County, MD
    '24029': 'kent2024', #Kent County, MD
    '24031': 'montgomery2024', #Montgomery County, MD
    '24033': "prince george's2024", #Prince George's County, MD
    '24035': "queen anne's2024", #Queen Anne's County, MD
    '24037': "st. mary's2024", #St. Mary's County, MD
    '24039': 'somerset2024', #Somerset County, MD
    '24041': 'talbot2024', #Talbot County, MD
    '24043': 'washington2024', #Washington County, MD
    '24045': 'wicomico2024', #Wicomico County, MD
    '24047': 'worcester2024', #Worcester County, MD
    '24510': 'baltimore city2024', #Baltimore City County, MD
    '25001': 'barnstable2024', #Barnstable County, MA
    '25003': 'berkshire2024', #Berkshire County, MA
    '25005': 'bristol2024', #Bristol County, MA
    '25007': 'dukes2024', #Dukes County, MA
    '25009': 'essex2024', #Essex County, MA
    '25011': 'franklin2024', #Franklin County, MA
    '25013': 'hampden2024', #Hampden County, MA
    '25015': 'hampshire2024', #Hampshire County, MA
    '25017': 'middlesex2024', #Middlesex County, MA
    '25019': 'nantucket2024', #Nantucket County, MA
    '25021': 'norfolk2024', #Norfolk County, MA
    '25023': 'plymouth2024', #Plymouth County, MA
    '25025': 'suffolk2024', #Suffolk County, MA
    '25027': 'worcester2024', #Worcester County, MA
    '26001': 'alcona2024', #Alcona County, MI
    '26003': 'alger2024', #Alger County, MI
    '26005': 'allegan2024', #Allegan County, MI
    '26007': 'alpena2024', #Alpena County, MI
    '26009': 'antrim2024', #Antrim County, MI
    '26011': 'arenac2024', #Arenac County, MI
    '26013': 'baraga2024', #Baraga County, MI
    '26015': 'barry2024', #Barry County, MI
    '26017': 'bay2024', #Bay County, MI
    '26019': 'benzie2024', #Benzie County, MI
    '26021': 'berrien2024', #Berrien County, MI
    '26023': 'branch2024', #Branch County, MI
    '26025': 'calhoun2024', #Calhoun County, MI
    '26027': 'cass2024', #Cass County, MI
    '26029': 'charlevoix2024', #Charlevoix County, MI
    '26031': 'cheboygan2024', #Cheboygan County, MI
    '26033': 'chippewa2024', #Chippewa County, MI
    '26035': 'clare2024', #Clare County, MI
    '26037': 'clinton2024', #Clinton County, MI
    '26039': 'crawford2024', #Crawford County, MI
    '26041': 'delta2024', #Delta County, MI
    '26043': 'dickinson2024', #Dickinson County, MI
    '26045': 'eaton2024', #Eaton County, MI
    '26047': 'emmet2024', #Emmet County, MI
    '26049': 'genesee2024', #Genesee County, MI
    '26051': 'gladwin2024', #Gladwin County, MI
    '26053': 'gogebic2024', #Gogebic County, MI
    '26055': 'grand traverse2024', #Grand Traverse County, MI
    '26057': 'gratiot2024', #Gratiot County, MI
    '26059': 'hillsdale2024', #Hillsdale County, MI
    '26061': 'houghton2024', #Houghton County, MI
    '26063': 'huron2024', #Huron County, MI
    '26065': 'ingham2024', #Ingham County, MI
    '26067': 'ionia2024', #Ionia County, MI
    '26069': 'iosco2024', #Iosco County, MI
    '26071': 'iron2024', #Iron County, MI
    '26073': 'isabella2024', #Isabella County, MI
    '26075': 'jackson2024', #Jackson County, MI
    '26077': 'kalamazoo2024', #Kalamazoo County, MI
    '26079': 'kalkaska2024', #Kalkaska County, MI
    '26081': 'kent2024', #Kent County, MI
    '26083': 'keweenaw2024', #Keweenaw County, MI
    '26085': 'lake2024', #Lake County, MI
    '26087': 'lapeer2024', #Lapeer County, MI
    '26089': 'leelanau2024', #Leelanau County, MI
    '26091': 'lenawee2024', #Lenawee County, MI
    '26093': 'livingston2024', #Livingston County, MI
    '26095': 'luce2024', #Luce County, MI
    '26097': 'mackinac2024', #Mackinac County, MI
    '26099': 'macomb2024', #Macomb County, MI
    '26101': 'manistee2024', #Manistee County, MI
    '26103': 'marquette2024', #Marquette County, MI
    '26105': 'mason2024', #Mason County, MI
    '26107': 'mecosta2024', #Mecosta County, MI
    '26109': 'menominee2024', #Menominee County, MI
    '26111': 'midland2024', #Midland County, MI
    '26113': 'missaukee2024', #Missaukee County, MI
    '26115': 'monroe2024', #Monroe County, MI
    '26117': 'montcalm2024', #Montcalm County, MI
    '26119': 'montmorency2024', #Montmorency County, MI
    '26121': 'muskegon2024', #Muskegon County, MI
    '26123': 'newaygo2024', #Newaygo County, MI
    '26125': 'oakland2024', #Oakland County, MI
    '26127': 'oceana2024', #Oceana County, MI
    '26129': 'ogemaw2024', #Ogemaw County, MI
    '26131': 'ontonagon2024', #Ontonagon County, MI
    '26133': 'osceola2024', #Osceola County, MI
    '26135': 'oscoda2024', #Oscoda County, MI
    '26137': 'otsego2024', #Otsego County, MI
    '26139': 'ottawa2024', #Ottawa County, MI
    '26141': 'presque isle2024', #Presque Isle County, MI
    '26143': 'roscommon2024', #Roscommon County, MI
    '26145': 'saginaw2024', #Saginaw County, MI
    '26147': 'st. clair2024', #St. Clair County, MI
    '26149': 'st. joseph2024', #St. Joseph County, MI
    '26151': 'sanilac2024', #Sanilac County, MI
    '26153': 'schoolcraft2024', #Schoolcraft County, MI
    '26155': 'shiawassee2024', #Shiawassee County, MI
    '26157': 'tuscola2024', #Tuscola County, MI
    '26159': 'van buren2024', #Van Buren County, MI
    '26161': 'washtenaw2024', #Washtenaw County, MI
    '26163': 'wayne2024', #Wayne County, MI
    '26165': 'wexford2024', #Wexford County, MI
    '27001': 'aitkin2024', #Aitkin County, MN
    '27003': 'anoka2024', #Anoka County, MN
    '27005': 'becker2024', #Becker County, MN
    '27007': 'beltrami2024', #Beltrami County, MN
    '27009': 'benton2024', #Benton County, MN
    '27011': 'big stone2024', #Big Stone County, MN
    '27013': 'blue earth2024', #Blue Earth County, MN
    '27015': 'brown2024', #Brown County, MN
    '27017': 'carlton2024', #Carlton County, MN
    '27019': 'carver2024', #Carver County, MN
    '27021': 'cass2024', #Cass County, MN
    '27023': 'chippewa2024', #Chippewa County, MN
    '27025': 'chisago2024', #Chisago County, MN
    '27027': 'clay2024', #Clay County, MN
    '27029': 'clearwater2024', #Clearwater County, MN
    '27031': 'cook2024', #Cook County, MN
    '27033': 'cottonwood2024', #Cottonwood County, MN
    '27035': 'crow wing2024', #Crow Wing County, MN
    '27037': 'dakota2024', #Dakota County, MN
    '27039': 'dodge2024', #Dodge County, MN
    '27041': 'douglas2024', #Douglas County, MN
    '27043': 'faribault2024', #Faribault County, MN
    '27045': 'fillmore2024', #Fillmore County, MN
    '27047': 'freeborn2024', #Freeborn County, MN
    '27049': 'goodhue2024', #Goodhue County, MN
    '27051': 'grant2024', #Grant County, MN
    '27053': 'hennepin2024', #Hennepin County, MN
    '27055': 'houston2024', #Houston County, MN
    '27057': 'hubbard2024', #Hubbard County, MN
    '27059': 'isanti2024', #Isanti County, MN
    '27061': 'itasca2024', #Itasca County, MN
    '27063': 'jackson2024', #Jackson County, MN
    '27065': 'kanabec2024', #Kanabec County, MN
    '27067': 'kandiyohi2024', #Kandiyohi County, MN
    '27069': 'kittson2024', #Kittson County, MN
    '27071': 'koochiching2024', #Koochiching County, MN
    '27073': 'lac qui parle2024', #Lac qui Parle County, MN
    '27075': 'lake2024', #Lake County, MN
    '27077': 'lake of the woods2024', #Lake of the Woods County, MN
    '27079': 'le sueur2024', #Le Sueur County, MN
    '27081': 'lincoln2024', #Lincoln County, MN
    '27083': 'lyon2024', #Lyon County, MN
    '27085': 'mcleod2024', #McLeod County, MN
    '27087': 'mahnomen2024', #Mahnomen County, MN
    '27089': 'marshall2024', #Marshall County, MN
    '27091': 'martin2024', #Martin County, MN
    '27093': 'meeker2024', #Meeker County, MN
    '27095': 'mille lacs2024', #Mille Lacs County, MN
    '27097': 'morrison2024', #Morrison County, MN
    '27099': 'mower2024', #Mower County, MN
    '27101': 'murray2024', #Murray County, MN
    '27103': 'nicollet2024', #Nicollet County, MN
    '27105': 'nobles2024', #Nobles County, MN
    '27107': 'norman2024', #Norman County, MN
    '27109': 'olmsted2024', #Olmsted County, MN
    '27111': 'otter tail2024', #Otter Tail County, MN
    '27113': 'pennington2024', #Pennington County, MN
    '27115': 'pine2024', #Pine County, MN
    '27117': 'pipestone2024', #Pipestone County, MN
    '27119': 'polk2024', #Polk County, MN
    '27121': 'pope2024', #Pope County, MN
    '27123': 'ramsey2024', #Ramsey County, MN
    '27125': 'red lake2024', #Red Lake County, MN
    '27127': 'redwood2024', #Redwood County, MN
    '27129': 'renville2024', #Renville County, MN
    '27131': 'rice2024', #Rice County, MN
    '27133': 'rock2024', #Rock County, MN
    '27135': 'roseau2024', #Roseau County, MN
    '27137': 'st. louis2024', #St. Louis County, MN
    '27139': 'scott2024', #Scott County, MN
    '27141': 'sherburne2024', #Sherburne County, MN
    '27143': 'sibley2024', #Sibley County, MN
    '27145': 'stearns2024', #Stearns County, MN
    '27147': 'steele2024', #Steele County, MN
    '27149': 'stevens2024', #Stevens County, MN
    '27151': 'swift2024', #Swift County, MN
    '27153': 'todd2024', #Todd County, MN
    '27155': 'traverse2024', #Traverse County, MN
    '27157': 'wabasha2024', #Wabasha County, MN
    '27159': 'wadena2024', #Wadena County, MN
    '27161': 'waseca2024', #Waseca County, MN
    '27163': 'washington2024', #Washington County, MN
    '27165': 'watonwan2024', #Watonwan County, MN
    '27167': 'wilkin2024', #Wilkin County, MN
    '27169': 'winona2024', #Winona County, MN
    '27171': 'wright2024', #Wright County, MN
    '27173': 'yellow medicine2024', #Yellow Medicine County, MN
    '28001': 'adams2024', #Adams County, MS
    '28003': 'alcorn2024', #Alcorn County, MS
    '28005': 'amite2024', #Amite County, MS
    '28007': 'attala2024', #Attala County, MS
    '28009': 'benton2024', #Benton County, MS
    '28011': 'bolivar2024', #Bolivar County, MS
    '28013': 'calhoun2024', #Calhoun County, MS
    '28015': 'carroll2024', #Carroll County, MS
    '28017': 'chickasaw2024', #Chickasaw County, MS
    '28019': 'choctaw2024', #Choctaw County, MS
    '28021': 'claiborne2024', #Claiborne County, MS
    '28023': 'clarke2024', #Clarke County, MS
    '28025': 'clay2024', #Clay County, MS
    '28027': 'coahoma2024', #Coahoma County, MS
    '28029': 'copiah2024', #Copiah County, MS
    '28031': 'covington2024', #Covington County, MS
    '28033': 'desoto2024', #DeSoto County, MS
    '28035': 'forrest2024', #Forrest County, MS
    '28037': 'franklin2024', #Franklin County, MS
    '28039': 'george2024', #George County, MS
    '28041': 'greene2024', #Greene County, MS
    '28043': 'grenada2024', #Grenada County, MS
    '28045': 'hancock2024', #Hancock County, MS
    '28047': 'harrison2024', #Harrison County, MS
    '28049': 'hinds2024', #Hinds County, MS
    '28051': 'holmes2024', #Holmes County, MS
    '28053': 'humphreys2024', #Humphreys County, MS
    '28055': 'issaquena2024', #Issaquena County, MS
    '28057': 'itawamba2024', #Itawamba County, MS
    '28059': 'jackson2024', #Jackson County, MS
    '28061': 'jasper2024', #Jasper County, MS
    '28063': 'jefferson2024', #Jefferson County, MS
    '28065': 'jefferson davis2024', #Jefferson Davis County, MS
    '28067': 'jones2024', #Jones County, MS
    '28069': 'kemper2024', #Kemper County, MS
    '28071': 'lafayette2024', #Lafayette County, MS
    '28073': 'lamar2024', #Lamar County, MS
    '28075': 'lauderdale2024', #Lauderdale County, MS
    '28077': 'lawrence2024', #Lawrence County, MS
    '28079': 'leake2024', #Leake County, MS
    '28081': 'lee2024', #Lee County, MS
    '28083': 'leflore2024', #Leflore County, MS
    '28085': 'lincoln2024', #Lincoln County, MS
    '28087': 'lowndes2024', #Lowndes County, MS
    '28089': 'madison2024', #Madison County, MS
    '28091': 'marion2024', #Marion County, MS
    '28093': 'marshall2024', #Marshall County, MS
    '28095': 'monroe2024', #Monroe County, MS
    '28097': 'montgomery2024', #Montgomery County, MS
    '28099': 'neshoba2024', #Neshoba County, MS
    '28101': 'newton2024', #Newton County, MS
    '28103': 'noxubee2024', #Noxubee County, MS
    '28105': 'oktibbeha2024', #Oktibbeha County, MS
    '28107': 'panola2024', #Panola County, MS
    '28109': 'pearl river2024', #Pearl River County, MS
    '28111': 'perry2024', #Perry County, MS
    '28113': 'pike2024', #Pike County, MS
    '28115': 'pontotoc2024', #Pontotoc County, MS
    '28117': 'prentiss2024', #Prentiss County, MS
    '28119': 'quitman2024', #Quitman County, MS
    '28121': 'rankin2024', #Rankin County, MS
    '28123': 'scott2024', #Scott County, MS
    '28125': 'sharkey2024', #Sharkey County, MS
    '28127': 'simpson2024', #Simpson County, MS
    '28129': 'smith2024', #Smith County, MS
    '28131': 'stone2024', #Stone County, MS
    '28133': 'sunflower2024', #Sunflower County, MS
    '28135': 'tallahatchie2024', #Tallahatchie County, MS
    '28137': 'tate2024', #Tate County, MS
    '28139': 'tippah2024', #Tippah County, MS
    '28141': 'tishomingo2024', #Tishomingo County, MS
    '28143': 'tunica2024', #Tunica County, MS
    '28145': 'union2024', #Union County, MS
    '28147': 'walthall2024', #Walthall County, MS
    '28149': 'warren2024', #Warren County, MS
    '28151': 'washington2024', #Washington County, MS
    '28153': 'wayne2024', #Wayne County, MS
    '28155': 'webster2024', #Webster County, MS
    '28157': 'wilkinson2024', #Wilkinson County, MS
    '28159': 'winston2024', #Winston County, MS
    '28161': 'yalobusha2024', #Yalobusha County, MS
    '28163': 'yazoo2024', #Yazoo County, MS
    '29001': 'adair2024', #Adair County, MO
    '29003': 'andrew2024', #Andrew County, MO
    '29005': 'atchison2024', #Atchison County, MO
    '29007': 'audrain2024', #Audrain County, MO
    '29009': 'barry2024', #Barry County, MO
    '29011': 'barton2024', #Barton County, MO
    '29013': 'bates2024', #Bates County, MO
    '29015': 'benton2024', #Benton County, MO
    '29017': 'bollinger2024', #Bollinger County, MO
    '29019': 'boone2024', #Boone County, MO
    '29021': 'buchanan2024', #Buchanan County, MO
    '29023': 'butler2024', #Butler County, MO
    '29025': 'caldwell2024', #Caldwell County, MO
    '29027': 'callaway2024', #Callaway County, MO
    '29029': 'camden2024', #Camden County, MO
    '29031': 'cape girardeau2024', #Cape Girardeau County, MO
    '29033': 'carroll2024', #Carroll County, MO
    '29035': 'carter2024', #Carter County, MO
    '29037': 'cass2024', #Cass County, MO
    '29039': 'cedar2024', #Cedar County, MO
    '29041': 'chariton2024', #Chariton County, MO
    '29043': 'christian2024', #Christian County, MO
    '29045': 'clark2024', #Clark County, MO
    '29047': 'clay2024', #Clay County, MO
    '29049': 'clinton2024', #Clinton County, MO
    '29051': 'cole2024', #Cole County, MO
    '29053': 'cooper2024', #Cooper County, MO
    '29055': 'crawford2024', #Crawford County, MO
    '29057': 'dade2024', #Dade County, MO
    '29059': 'dallas2024', #Dallas County, MO
    '29061': 'daviess2024', #Daviess County, MO
    '29063': 'dekalb2024', #DeKalb County, MO
    '29065': 'dent2024', #Dent County, MO
    '29067': 'douglas2024', #Douglas County, MO
    '29069': 'dunklin2024', #Dunklin County, MO
    '29071': 'franklin2024', #Franklin County, MO
    '29073': 'gasconade2024', #Gasconade County, MO
    '29075': 'gentry2024', #Gentry County, MO
    '29077': 'greene2024', #Greene County, MO
    '29079': 'grundy2024', #Grundy County, MO
    '29081': 'harrison2024', #Harrison County, MO
    '29083': 'henry2024', #Henry County, MO
    '29085': 'hickory2024', #Hickory County, MO
    '29087': 'holt2024', #Holt County, MO
    '29089': 'howard2024', #Howard County, MO
    '29091': 'howell2024', #Howell County, MO
    '29093': 'iron2024', #Iron County, MO
    '29095': 'jackson2024', #Jackson County, MO
    '29097': 'jasper2024', #Jasper County, MO
    '29099': 'jefferson2024', #Jefferson County, MO
    '29101': 'johnson2024', #Johnson County, MO
    '29103': 'knox2024', #Knox County, MO
    '29105': 'laclede2024', #Laclede County, MO
    '29107': 'lafayette2024', #Lafayette County, MO
    '29109': 'lawrence2024', #Lawrence County, MO
    '29111': 'lewis2024', #Lewis County, MO
    '29113': 'lincoln2024', #Lincoln County, MO
    '29115': 'linn2024', #Linn County, MO
    '29117': 'livingston2024', #Livingston County, MO
    '29119': 'mcdonald2024', #McDonald County, MO
    '29121': 'macon2024', #Macon County, MO
    '29123': 'madison2024', #Madison County, MO
    '29125': 'maries2024', #Maries County, MO
    '29127': 'marion2024', #Marion County, MO
    '29129': 'mercer2024', #Mercer County, MO
    '29131': 'miller2024', #Miller County, MO
    '29133': 'mississippi2024', #Mississippi County, MO
    '29135': 'moniteau2024', #Moniteau County, MO
    '29137': 'monroe2024', #Monroe County, MO
    '29139': 'montgomery2024', #Montgomery County, MO
    '29141': 'morgan2024', #Morgan County, MO
    '29143': 'new madrid2024', #New Madrid County, MO
    '29145': 'newton2024', #Newton County, MO
    '29147': 'nodaway2024', #Nodaway County, MO
    '29149': 'oregon2024', #Oregon County, MO
    '29151': 'osage2024', #Osage County, MO
    '29153': 'ozark2024', #Ozark County, MO
    '29155': 'pemiscot2024', #Pemiscot County, MO
    '29157': 'perry2024', #Perry County, MO
    '29159': 'pettis2024', #Pettis County, MO
    '29161': 'phelps2024', #Phelps County, MO
    '29163': 'pike2024', #Pike County, MO
    '29165': 'platte2024', #Platte County, MO
    '29167': 'polk2024', #Polk County, MO
    '29169': 'pulaski2024', #Pulaski County, MO
    '29171': 'putnam2024', #Putnam County, MO
    '29173': 'ralls2024', #Ralls County, MO
    '29175': 'randolph2024', #Randolph County, MO
    '29177': 'ray2024', #Ray County, MO
    '29179': 'reynolds2024', #Reynolds County, MO
    '29181': 'ripley2024', #Ripley County, MO
    '29183': 'st. charles2024', #St. Charles County, MO
    '29185': 'st. clair2024', #St. Clair County, MO
    '29186': 'ste. genevieve2024', #Ste. Genevieve County, MO
    '29187': 'st. francois2024', #St. Francois County, MO
    '29189': 'st. louis2024', #St. Louis County, MO
    '29195': 'saline2024', #Saline County, MO
    '29197': 'schuyler2024', #Schuyler County, MO
    '29199': 'scotland2024', #Scotland County, MO
    '29201': 'scott2024', #Scott County, MO
    '29203': 'shannon2024', #Shannon County, MO
    '29205': 'shelby2024', #Shelby County, MO
    '29207': 'stoddard2024', #Stoddard County, MO
    '29209': 'stone2024', #Stone County, MO
    '29211': 'sullivan2024', #Sullivan County, MO
    '29213': 'taney2024', #Taney County, MO
    '29215': 'texas2024', #Texas County, MO
    '29217': 'vernon2024', #Vernon County, MO
    '29219': 'warren2024', #Warren County, MO
    '29221': 'washington2024', #Washington County, MO
    '29223': 'wayne2024', #Wayne County, MO
    '29225': 'webster2024', #Webster County, MO
    '29227': 'worth2024', #Worth County, MO
    '29229': 'wright2024', #Wright County, MO
    '29510': 'st. louis city2024', #St. Louis City County, MO
    '30001': 'beaverhead2024', #Beaverhead County, MT
    '30003': 'big horn2024', #Big Horn County, MT
    '30005': 'blaine2024', #Blaine County, MT
    '30007': 'broadwater2024', #Broadwater County, MT
    '30009': 'carbon2024', #Carbon County, MT
    '30011': 'carter2024', #Carter County, MT
    '30013': 'cascade2024', #Cascade County, MT
    '30015': 'chouteau2024', #Chouteau County, MT
    '30017': 'custer2024', #Custer County, MT
    '30019': 'daniels2024', #Daniels County, MT
    '30021': 'dawson2024', #Dawson County, MT
    '30023': 'deer lodge2024', #Deer Lodge County, MT
    '30025': 'fallon2024', #Fallon County, MT
    '30027': 'fergus2024', #Fergus County, MT
    '30029': 'flathead2024', #Flathead County, MT
    '30031': 'gallatin2024', #Gallatin County, MT
    '30033': 'garfield2024', #Garfield County, MT
    '30035': 'glacier2024', #Glacier County, MT
    '30037': 'golden valley2024', #Golden Valley County, MT
    '30039': 'granite2024', #Granite County, MT
    '30041': 'hill2024', #Hill County, MT
    '30043': 'jefferson2024', #Jefferson County, MT
    '30045': 'judith basin2024', #Judith Basin County, MT
    '30047': 'lake2024', #Lake County, MT
    '30049': 'lewis and clark2024', #Lewis and Clark County, MT
    '30051': 'liberty2024', #Liberty County, MT
    '30053': 'lincoln2024', #Lincoln County, MT
    '30055': 'mccone2024', #McCone County, MT
    '30057': 'madison2024', #Madison County, MT
    '30059': 'meagher2024', #Meagher County, MT
    '30061': 'mineral2024', #Mineral County, MT
    '30063': 'missoula2024', #Missoula County, MT
    '30065': 'musselshell2024', #Musselshell County, MT
    '30067': 'park2024', #Park County, MT
    '30069': 'petroleum2024', #Petroleum County, MT
    '30071': 'phillips2024', #Phillips County, MT
    '30073': 'pondera2024', #Pondera County, MT
    '30075': 'powder river2024', #Powder River County, MT
    '30077': 'powell2024', #Powell County, MT
    '30079': 'prairie2024', #Prairie County, MT
    '30081': 'ravalli2024', #Ravalli County, MT
    '30083': 'richland2024', #Richland County, MT
    '30085': 'roosevelt2024', #Roosevelt County, MT
    '30087': 'rosebud2024', #Rosebud County, MT
    '30089': 'sanders2024', #Sanders County, MT
    '30091': 'sheridan2024', #Sheridan County, MT
    '30093': 'silver bow2024', #Silver Bow County, MT
    '30095': 'stillwater2024', #Stillwater County, MT
    '30097': 'sweet grass2024', #Sweet Grass County, MT
    '30099': 'teton2024', #Teton County, MT
    '30101': 'toole2024', #Toole County, MT
    '30103': 'treasure2024', #Treasure County, MT
    '30105': 'valley2024', #Valley County, MT
    '30107': 'wheatland2024', #Wheatland County, MT
    '30109': 'wibaux2024', #Wibaux County, MT
    '30111': 'yellowstone2024', #Yellowstone County, MT
    '31001': 'adams2024', #Adams County, NE
    '31003': 'antelope2024', #Antelope County, NE
    '31005': 'arthur2024', #Arthur County, NE
    '31007': 'banner2024', #Banner County, NE
    '31009': 'blaine2024', #Blaine County, NE
    '31011': 'boone2024', #Boone County, NE
    '31013': 'box butte2024', #Box Butte County, NE
    '31015': 'boyd2024', #Boyd County, NE
    '31017': 'brown2024', #Brown County, NE
    '31019': 'buffalo2024', #Buffalo County, NE
    '31021': 'burt2024', #Burt County, NE
    '31023': 'butler2024', #Butler County, NE
    '31025': 'cass2024', #Cass County, NE
    '31027': 'cedar2024', #Cedar County, NE
    '31029': 'chase2024', #Chase County, NE
    '31031': 'cherry2024', #Cherry County, NE
    '31033': 'cheyenne2024', #Cheyenne County, NE
    '31035': 'clay2024', #Clay County, NE
    '31037': 'colfax2024', #Colfax County, NE
    '31039': 'cuming2024', #Cuming County, NE
    '31041': 'custer2024', #Custer County, NE
    '31043': 'dakota2024', #Dakota County, NE
    '31045': 'dawes2024', #Dawes County, NE
    '31047': 'dawson2024', #Dawson County, NE
    '31049': 'deuel2024', #Deuel County, NE
    '31051': 'dixon2024', #Dixon County, NE
    '31053': 'dodge2024', #Dodge County, NE
    '31055': 'douglas2024', #Douglas County, NE
    '31057': 'dundy2024', #Dundy County, NE
    '31059': 'fillmore2024', #Fillmore County, NE
    '31061': 'franklin2024', #Franklin County, NE
    '31063': 'frontier2024', #Frontier County, NE
    '31065': 'furnas2024', #Furnas County, NE
    '31067': 'gage2024', #Gage County, NE
    '31069': 'garden2024', #Garden County, NE
    '31071': 'garfield2024', #Garfield County, NE
    '31073': 'gosper2024', #Gosper County, NE
    '31075': 'grant2024', #Grant County, NE
    '31077': 'greeley2024', #Greeley County, NE
    '31079': 'hall2024', #Hall County, NE
    '31081': 'hamilton2024', #Hamilton County, NE
    '31083': 'harlan2024', #Harlan County, NE
    '31085': 'hayes2024', #Hayes County, NE
    '31087': 'hitchcock2024', #Hitchcock County, NE
    '31089': 'holt2024', #Holt County, NE
    '31091': 'hooker2024', #Hooker County, NE
    '31093': 'howard2024', #Howard County, NE
    '31095': 'jefferson2024', #Jefferson County, NE
    '31097': 'johnson2024', #Johnson County, NE
    '31099': 'kearney2024', #Kearney County, NE
    '31101': 'keith2024', #Keith County, NE
    '31103': 'keya paha2024', #Keya Paha County, NE
    '31105': 'kimball2024', #Kimball County, NE
    '31107': 'knox2024', #Knox County, NE
    '31109': 'lancaster2024', #Lancaster County, NE
    '31111': 'lincoln2024', #Lincoln County, NE
    '31113': 'logan2024', #Logan County, NE
    '31115': 'loup2024', #Loup County, NE
    '31117': 'mcpherson2024', #McPherson County, NE
    '31119': 'madison2024', #Madison County, NE
    '31121': 'merrick2024', #Merrick County, NE
    '31123': 'morrill2024', #Morrill County, NE
    '31125': 'nance2024', #Nance County, NE
    '31127': 'nemaha2024', #Nemaha County, NE
    '31129': 'nuckolls2024', #Nuckolls County, NE
    '31131': 'otoe2024', #Otoe County, NE
    '31133': 'pawnee2024', #Pawnee County, NE
    '31135': 'perkins2024', #Perkins County, NE
    '31137': 'phelps2024', #Phelps County, NE
    '31139': 'pierce2024', #Pierce County, NE
    '31141': 'platte2024', #Platte County, NE
    '31143': 'polk2024', #Polk County, NE
    '31145': 'red willow2024', #Red Willow County, NE
    '31147': 'richardson2024', #Richardson County, NE
    '31149': 'rock2024', #Rock County, NE
    '31151': 'saline2024', #Saline County, NE
    '31153': 'sarpy2024', #Sarpy County, NE
    '31155': 'saunders2024', #Saunders County, NE
    '31157': 'scotts bluff2024', #Scotts Bluff County, NE
    '31159': 'seward2024', #Seward County, NE
    '31161': 'sheridan2024', #Sheridan County, NE
    '31163': 'sherman2024', #Sherman County, NE
    '31165': 'sioux2024', #Sioux County, NE
    '31167': 'stanton2024', #Stanton County, NE
    '31169': 'thayer2024', #Thayer County, NE
    '31171': 'thomas2024', #Thomas County, NE
    '31173': 'thurston2024', #Thurston County, NE
    '31175': 'valley2024', #Valley County, NE
    '31177': 'washington2024', #Washington County, NE
    '31179': 'wayne2024', #Wayne County, NE
    '31181': 'webster2024', #Webster County, NE
    '31183': 'wheeler2024', #Wheeler County, NE
    '31185': 'york2024', #York County, NE
    '32001': 'churchill2024', #Churchill County, NV
    '32003': 'clark2024', #Clark County, NV
    '32005': 'douglas2024', #Douglas County, NV
    '32007': 'elko2024', #Elko County, NV
    '32009': 'esmeralda2024', #Esmeralda County, NV
    '32011': 'eureka2024', #Eureka County, NV
    '32013': 'humboldt2024', #Humboldt County, NV
    '32015': 'lander2024', #Lander County, NV
    '32017': 'lincoln2024', #Lincoln County, NV
    '32019': 'lyon2024', #Lyon County, NV
    '32021': 'mineral2024', #Mineral County, NV
    '32023': 'nye2024', #Nye County, NV
    '32027': 'pershing2024', #Pershing County, NV
    '32029': 'storey2024', #Storey County, NV
    '32031': 'washoe2024', #Washoe County, NV
    '32033': 'white pine2024', #White Pine County, NV
    '32510': 'carson city2024', #Carson City County, NV
    '33001': 'belknap2024', #Belknap County, NH
    '33003': 'carroll2024', #Carroll County, NH
    '33005': 'cheshire2024', #Cheshire County, NH
    '33007': 'coos2024', #Coos County, NH
    '33009': 'grafton2024', #Grafton County, NH
    '33011': 'hillsborough2024', #Hillsborough County, NH
    '33013': 'merrimack2024', #Merrimack County, NH
    '33015': 'rockingham2024', #Rockingham County, NH
    '33017': 'strafford2024', #Strafford County, NH
    '33019': 'sullivan2024', #Sullivan County, NH
    '34001': 'atlantic2024', #Atlantic County, NJ
    '34003': 'bergen2024', #Bergen County, NJ
    '34005': 'burlington2024', #Burlington County, NJ
    '34007': 'camden2024', #Camden County, NJ
    '34009': 'cape may2024', #Cape May County, NJ
    '34011': 'cumberland2024', #Cumberland County, NJ
    '34013': 'essex2024', #Essex County, NJ
    '34015': 'gloucester2024', #Gloucester County, NJ
    '34017': 'hudson2024', #Hudson County, NJ
    '34019': 'hunterdon2024', #Hunterdon County, NJ
    '34021': 'mercer2024', #Mercer County, NJ
    '34023': 'middlesex2024', #Middlesex County, NJ
    '34025': 'monmouth2024', #Monmouth County, NJ
    '34027': 'morris2024', #Morris County, NJ
    '34029': 'ocean2024', #Ocean County, NJ
    '34031': 'passaic2024', #Passaic County, NJ
    '34033': 'salem2024', #Salem County, NJ
    '34035': 'somerset2024', #Somerset County, NJ
    '34037': 'sussex2024', #Sussex County, NJ
    '34039': 'union2024', #Union County, NJ
    '34041': 'warren2024', #Warren County, NJ
    '35001': 'bernalillo2024', #Bernalillo County, NM
    '35003': 'catron2024', #Catron County, NM
    '35005': 'chaves2024', #Chaves County, NM
    '35006': 'cibola2024', #Cibola County, NM
    '35007': 'colfax2024', #Colfax County, NM
    '35009': 'curry2024', #Curry County, NM
    '35011': 'de baca2024', #De Baca County, NM
    '35013': 'dona ana2024', #Dona Ana County, NM
    '35015': 'eddy2024', #Eddy County, NM
    '35017': 'grant2024', #Grant County, NM
    '35019': 'guadalupe2024', #Guadalupe County, NM
    '35021': 'harding2024', #Harding County, NM
    '35023': 'hidalgo2024', #Hidalgo County, NM
    '35025': 'lea2024', #Lea County, NM
    '35027': 'lincoln2024', #Lincoln County, NM
    '35028': 'los alamos2024', #Los Alamos County, NM
    '35029': 'luna2024', #Luna County, NM
    '35031': 'mckinley2024', #McKinley County, NM
    '35033': 'mora2024', #Mora County, NM
    '35035': 'otero2024', #Otero County, NM
    '35037': 'quay2024', #Quay County, NM
    '35039': 'rio arriba2024', #Rio Arriba County, NM
    '35041': 'roosevelt2024', #Roosevelt County, NM
    '35043': 'sandoval2024', #Sandoval County, NM
    '35045': 'san juan2024', #San Juan County, NM
    '35047': 'san miguel2024', #San Miguel County, NM
    '35049': 'santa fe2024', #Santa Fe County, NM
    '35051': 'sierra2024', #Sierra County, NM
    '35053': 'socorro2024', #Socorro County, NM
    '35055': 'taos2024', #Taos County, NM
    '35057': 'torrance2024', #Torrance County, NM
    '35059': 'union2024', #Union County, NM
    '35061': 'valencia2024', #Valencia County, NM
    '36001': 'albany2024', #Albany County, NY
    '36003': 'allegany2024', #Allegany County, NY
    '36005': 'bronx2024', #Bronx County, NY
    '36007': 'broome2024', #Broome County, NY
    '36009': 'cattaraugus2024', #Cattaraugus County, NY
    '36011': 'cayuga2024', #Cayuga County, NY
    '36013': 'chautauqua2024', #Chautauqua County, NY
    '36015': 'chemung2024', #Chemung County, NY
    '36017': 'chenango2024', #Chenango County, NY
    '36019': 'clinton2024', #Clinton County, NY
    '36021': 'columbia2024', #Columbia County, NY
    '36023': 'cortland2024', #Cortland County, NY
    '36025': 'delaware2024', #Delaware County, NY
    '36027': 'dutchess2024', #Dutchess County, NY
    '36029': 'erie2024', #Erie County, NY
    '36031': 'essex2024', #Essex County, NY
    '36033': 'franklin2024', #Franklin County, NY
    '36035': 'fulton2024', #Fulton County, NY
    '36037': 'genesee2024', #Genesee County, NY
    '36039': 'greene2024', #Greene County, NY
    '36041': 'hamilton2024', #Hamilton County, NY
    '36043': 'herkimer2024', #Herkimer County, NY
    '36045': 'jefferson2024', #Jefferson County, NY
    '36047': 'kings2024', #Kings County, NY
    '36049': 'lewis2024', #Lewis County, NY
    '36051': 'livingston2024', #Livingston County, NY
    '36053': 'madison2024', #Madison County, NY
    '36055': 'monroe2024', #Monroe County, NY
    '36057': 'montgomery2024', #Montgomery County, NY
    '36059': 'nassau2024', #Nassau County, NY
    '36061': 'new york2024', #New York County, NY
    '36063': 'niagara2024', #Niagara County, NY
    '36065': 'oneida2024', #Oneida County, NY
    '36067': 'onondaga2024', #Onondaga County, NY
    '36069': 'ontario2024', #Ontario County, NY
    '36071': 'orange2024', #Orange County, NY
    '36073': 'orleans2024', #Orleans County, NY
    '36075': 'oswego2024', #Oswego County, NY
    '36077': 'otsego2024', #Otsego County, NY
    '36079': 'putnam2024', #Putnam County, NY
    '36081': 'queens2024', #Queens County, NY
    '36083': 'rensselaer2024', #Rensselaer County, NY
    '36085': 'richmond2024', #Richmond County, NY
    '36087': 'rockland2024', #Rockland County, NY
    '36089': 'st. lawrence2024', #St. Lawrence County, NY
    '36091': 'saratoga2024', #Saratoga County, NY
    '36093': 'schenectady2024', #Schenectady County, NY
    '36095': 'schoharie2024', #Schoharie County, NY
    '36097': 'schuyler2024', #Schuyler County, NY
    '36099': 'seneca2024', #Seneca County, NY
    '36101': 'steuben2024', #Steuben County, NY
    '36103': 'suffolk2024', #Suffolk County, NY
    '36105': 'sullivan2024', #Sullivan County, NY
    '36107': 'tioga2024', #Tioga County, NY
    '36109': 'tompkins2024', #Tompkins County, NY
    '36111': 'ulster2024', #Ulster County, NY
    '36113': 'warren2024', #Warren County, NY
    '36115': 'washington2024', #Washington County, NY
    '36117': 'wayne2024', #Wayne County, NY
    '36119': 'westchester2024', #Westchester County, NY
    '36121': 'wyoming2024', #Wyoming County, NY
    '36123': 'yates2024', #Yates County, NY
    '37001': 'alamance2024', #Alamance County, NC
    '37003': 'alexander2024', #Alexander County, NC
    '37005': 'alleghany2024', #Alleghany County, NC
    '37007': 'anson2024', #Anson County, NC
    '37009': 'ashe2024', #Ashe County, NC
    '37011': 'avery2024', #Avery County, NC
    '37013': 'beaufort2024', #Beaufort County, NC
    '37015': 'bertie2024', #Bertie County, NC
    '37017': 'bladen2024', #Bladen County, NC
    '37019': 'brunswick2024', #Brunswick County, NC
    '37021': 'buncombe2024', #Buncombe County, NC
    '37023': 'burke2024', #Burke County, NC
    '37025': 'cabarrus2024', #Cabarrus County, NC
    '37027': 'caldwell2024', #Caldwell County, NC
    '37029': 'camden2024', #Camden County, NC
    '37031': 'carteret2024', #Carteret County, NC
    '37033': 'caswell2024', #Caswell County, NC
    '37035': 'catawba2024', #Catawba County, NC
    '37037': 'chatham2024', #Chatham County, NC
    '37039': 'cherokee2024', #Cherokee County, NC
    '37041': 'chowan2024', #Chowan County, NC
    '37043': 'clay2024', #Clay County, NC
    '37045': 'cleveland2024', #Cleveland County, NC
    '37047': 'columbus2024', #Columbus County, NC
    '37049': 'craven2024', #Craven County, NC
    '37051': 'cumberland2024', #Cumberland County, NC
    '37053': 'currituck2024', #Currituck County, NC
    '37055': 'dare2024', #Dare County, NC
    '37057': 'davidson2024', #Davidson County, NC
    '37059': 'davie2024', #Davie County, NC
    '37061': 'duplin2024', #Duplin County, NC
    '37063': 'durham2024', #Durham County, NC
    '37065': 'edgecombe2024', #Edgecombe County, NC
    '37067': 'forsyth2024', #Forsyth County, NC
    '37069': 'franklin2024', #Franklin County, NC
    '37071': 'gaston2024', #Gaston County, NC
    '37073': 'gates2024', #Gates County, NC
    '37075': 'graham2024', #Graham County, NC
    '37077': 'granville2024', #Granville County, NC
    '37079': 'greene2024', #Greene County, NC
    '37081': 'guilford2024', #Guilford County, NC
    '37083': 'halifax2024', #Halifax County, NC
    '37085': 'harnett2024', #Harnett County, NC
    '37087': 'haywood2024', #Haywood County, NC
    '37089': 'henderson2024', #Henderson County, NC
    '37091': 'hertford2024', #Hertford County, NC
    '37093': 'hoke2024', #Hoke County, NC
    '37095': 'hyde2024', #Hyde County, NC
    '37097': 'iredell2024', #Iredell County, NC
    '37099': 'jackson2024', #Jackson County, NC
    '37101': 'johnston2024', #Johnston County, NC
    '37103': 'jones2024', #Jones County, NC
    '37105': 'lee2024', #Lee County, NC
    '37107': 'lenoir2024', #Lenoir County, NC
    '37109': 'lincoln2024', #Lincoln County, NC
    '37111': 'mcdowell2024', #McDowell County, NC
    '37113': 'macon2024', #Macon County, NC
    '37115': 'madison2024', #Madison County, NC
    '37117': 'martin2024', #Martin County, NC
    '37119': 'mecklenburg2024', #Mecklenburg County, NC
    '37121': 'mitchell2024', #Mitchell County, NC
    '37123': 'montgomery2024', #Montgomery County, NC
    '37125': 'moore2024', #Moore County, NC
    '37127': 'nash2024', #Nash County, NC
    '37129': 'new hanover2024', #New Hanover County, NC
    '37131': 'northampton2024', #Northampton County, NC
    '37133': 'onslow2024', #Onslow County, NC
    '37135': 'orange2024', #Orange County, NC
    '37137': 'pamlico2024', #Pamlico County, NC
    '37139': 'pasquotank2024', #Pasquotank County, NC
    '37141': 'pender2024', #Pender County, NC
    '37143': 'perquimans2024', #Perquimans County, NC
    '37145': 'person2024', #Person County, NC
    '37147': 'pitt2024', #Pitt County, NC
    '37149': 'polk2024', #Polk County, NC
    '37151': 'randolph2024', #Randolph County, NC
    '37153': 'richmond2024', #Richmond County, NC
    '37155': 'robeson2024', #Robeson County, NC
    '37157': 'rockingham2024', #Rockingham County, NC
    '37159': 'rowan2024', #Rowan County, NC
    '37161': 'rutherford2024', #Rutherford County, NC
    '37163': 'sampson2024', #Sampson County, NC
    '37165': 'scotland2024', #Scotland County, NC
    '37167': 'stanly2024', #Stanly County, NC
    '37169': 'stokes2024', #Stokes County, NC
    '37171': 'surry2024', #Surry County, NC
    '37173': 'swain2024', #Swain County, NC
    '37175': 'transylvania2024', #Transylvania County, NC
    '37177': 'tyrrell2024', #Tyrrell County, NC
    '37179': 'union2024', #Union County, NC
    '37181': 'vance2024', #Vance County, NC
    '37183': 'wake2024', #Wake County, NC
    '37185': 'warren2024', #Warren County, NC
    '37187': 'washington2024', #Washington County, NC
    '37189': 'watauga2024', #Watauga County, NC
    '37191': 'wayne2024', #Wayne County, NC
    '37193': 'wilkes2024', #Wilkes County, NC
    '37195': 'wilson2024', #Wilson County, NC
    '37197': 'yadkin2024', #Yadkin County, NC
    '37199': 'yancey2024', #Yancey County, NC
    '38001': 'adams2024', #Adams County, ND
    '38003': 'barnes2024', #Barnes County, ND
    '38005': 'benson2024', #Benson County, ND
    '38007': 'billings2024', #Billings County, ND
    '38009': 'bottineau2024', #Bottineau County, ND
    '38011': 'bowman2024', #Bowman County, ND
    '38013': 'burke2024', #Burke County, ND
    '38015': 'burleigh2024', #Burleigh County, ND
    '38017': 'cass2024', #Cass County, ND
    '38019': 'cavalier2024', #Cavalier County, ND
    '38021': 'dickey2024', #Dickey County, ND
    '38023': 'divide2024', #Divide County, ND
    '38025': 'dunn2024', #Dunn County, ND
    '38027': 'eddy2024', #Eddy County, ND
    '38029': 'emmons2024', #Emmons County, ND
    '38031': 'foster2024', #Foster County, ND
    '38033': 'golden valley2024', #Golden Valley County, ND
    '38035': 'grand forks2024', #Grand Forks County, ND
    '38037': 'grant2024', #Grant County, ND
    '38039': 'griggs2024', #Griggs County, ND
    '38041': 'hettinger2024', #Hettinger County, ND
    '38043': 'kidder2024', #Kidder County, ND
    '38045': 'lamoure2024', #LaMoure County, ND
    '38047': 'logan2024', #Logan County, ND
    '38049': 'mchenry2024', #McHenry County, ND
    '38051': 'mcintosh2024', #McIntosh County, ND
    '38053': 'mckenzie2024', #McKenzie County, ND
    '38055': 'mclean2024', #McLean County, ND
    '38057': 'mercer2024', #Mercer County, ND
    '38059': 'morton2024', #Morton County, ND
    '38061': 'mountrail2024', #Mountrail County, ND
    '38063': 'nelson2024', #Nelson County, ND
    '38065': 'oliver2024', #Oliver County, ND
    '38067': 'pembina2024', #Pembina County, ND
    '38069': 'pierce2024', #Pierce County, ND
    '38071': 'ramsey2024', #Ramsey County, ND
    '38073': 'ransom2024', #Ransom County, ND
    '38075': 'renville2024', #Renville County, ND
    '38077': 'richland2024', #Richland County, ND
    '38079': 'rolette2024', #Rolette County, ND
    '38081': 'sargent2024', #Sargent County, ND
    '38083': 'sheridan2024', #Sheridan County, ND
    '38085': 'sioux2024', #Sioux County, ND
    '38087': 'slope2024', #Slope County, ND
    '38089': 'stark2024', #Stark County, ND
    '38091': 'steele2024', #Steele County, ND
    '38093': 'stutsman2024', #Stutsman County, ND
    '38095': 'towner2024', #Towner County, ND
    '38097': 'traill2024', #Traill County, ND
    '38099': 'walsh2024', #Walsh County, ND
    '38101': 'ward2024', #Ward County, ND
    '38103': 'wells2024', #Wells County, ND
    '38105': 'williams2024', #Williams County, ND
    '39001': 'adams2024', #Adams County, OH
    '39003': 'allen2024', #Allen County, OH
    '39005': 'ashland2024', #Ashland County, OH
    '39007': 'ashtabula2024', #Ashtabula County, OH
    '39009': 'athens2024', #Athens County, OH
    '39011': 'auglaize2024', #Auglaize County, OH
    '39013': 'belmont2024', #Belmont County, OH
    '39015': 'brown2024', #Brown County, OH
    '39017': 'butler2024', #Butler County, OH
    '39019': 'carroll2024', #Carroll County, OH
    '39021': 'champaign2024', #Champaign County, OH
    '39023': 'clark2024', #Clark County, OH
    '39025': 'clermont2024', #Clermont County, OH
    '39027': 'clinton2024', #Clinton County, OH
    '39029': 'columbiana2024', #Columbiana County, OH
    '39031': 'coshocton2024', #Coshocton County, OH
    '39033': 'crawford2024', #Crawford County, OH
    '39035': 'cuyahoga2024', #Cuyahoga County, OH
    '39037': 'darke2024', #Darke County, OH
    '39039': 'defiance2024', #Defiance County, OH
    '39041': 'delaware2024', #Delaware County, OH
    '39043': 'erie2024', #Erie County, OH
    '39045': 'fairfield2024', #Fairfield County, OH
    '39047': 'fayette2024', #Fayette County, OH
    '39049': 'franklin2024', #Franklin County, OH
    '39051': 'fulton2024', #Fulton County, OH
    '39053': 'gallia2024', #Gallia County, OH
    '39055': 'geauga2024', #Geauga County, OH
    '39057': 'greene2024', #Greene County, OH
    '39059': 'guernsey2024', #Guernsey County, OH
    '39061': 'hamilton2024', #Hamilton County, OH
    '39063': 'hancock2024', #Hancock County, OH
    '39065': 'hardin2024', #Hardin County, OH
    '39067': 'harrison2024', #Harrison County, OH
    '39069': 'henry2024', #Henry County, OH
    '39071': 'highland2024', #Highland County, OH
    '39073': 'hocking2024', #Hocking County, OH
    '39075': 'holmes2024', #Holmes County, OH
    '39077': 'huron2024', #Huron County, OH
    '39079': 'jackson2024', #Jackson County, OH
    '39081': 'jefferson2024', #Jefferson County, OH
    '39083': 'knox2024', #Knox County, OH
    '39085': 'lake2024', #Lake County, OH
    '39087': 'lawrence2024', #Lawrence County, OH
    '39089': 'licking2024', #Licking County, OH
    '39091': 'logan2024', #Logan County, OH
    '39093': 'lorain2024', #Lorain County, OH
    '39095': 'lucas2024', #Lucas County, OH
    '39097': 'madison2024', #Madison County, OH
    '39099': 'mahoning2024', #Mahoning County, OH
    '39101': 'marion2024', #Marion County, OH
    '39103': 'medina2024', #Medina County, OH
    '39105': 'meigs2024', #Meigs County, OH
    '39107': 'mercer2024', #Mercer County, OH
    '39109': 'miami2024', #Miami County, OH
    '39111': 'monroe2024', #Monroe County, OH
    '39113': 'montgomery2024', #Montgomery County, OH
    '39115': 'morgan2024', #Morgan County, OH
    '39117': 'morrow2024', #Morrow County, OH
    '39119': 'muskingum2024', #Muskingum County, OH
    '39121': 'noble2024', #Noble County, OH
    '39123': 'ottawa2024', #Ottawa County, OH
    '39125': 'paulding2024', #Paulding County, OH
    '39127': 'perry2024', #Perry County, OH
    '39129': 'pickaway2024', #Pickaway County, OH
    '39131': 'pike2024', #Pike County, OH
    '39133': 'portage2024', #Portage County, OH
    '39135': 'preble2024', #Preble County, OH
    '39137': 'putnam2024', #Putnam County, OH
    '39139': 'richland2024', #Richland County, OH
    '39141': 'ross2024', #Ross County, OH
    '39143': 'sandusky2024', #Sandusky County, OH
    '39145': 'scioto2024', #Scioto County, OH
    '39147': 'seneca2024', #Seneca County, OH
    '39149': 'shelby2024', #Shelby County, OH
    '39151': 'stark2024', #Stark County, OH
    '39153': 'summit2024', #Summit County, OH
    '39155': 'trumbull2024', #Trumbull County, OH
    '39157': 'tuscarawas2024', #Tuscarawas County, OH
    '39159': 'union2024', #Union County, OH
    '39161': 'van wert2024', #Van Wert County, OH
    '39163': 'vinton2024', #Vinton County, OH
    '39165': 'warren2024', #Warren County, OH
    '39167': 'washington2024', #Washington County, OH
    '39169': 'wayne2024', #Wayne County, OH
    '39171': 'williams2024', #Williams County, OH
    '39173': 'wood2024', #Wood County, OH
    '39175': 'wyandot2024', #Wyandot County, OH
    '40001': 'adair2024', #Adair County, OK
    '40003': 'alfalfa2024', #Alfalfa County, OK
    '40005': 'atoka2024', #Atoka County, OK
    '40007': 'beaver2024', #Beaver County, OK
    '40009': 'beckham2024', #Beckham County, OK
    '40011': 'blaine2024', #Blaine County, OK
    '40013': 'bryan2024', #Bryan County, OK
    '40015': 'caddo2024', #Caddo County, OK
    '40017': 'canadian2024', #Canadian County, OK
    '40019': 'carter2024', #Carter County, OK
    '40021': 'cherokee2024', #Cherokee County, OK
    '40023': 'choctaw2024', #Choctaw County, OK
    '40025': 'cimarron2024', #Cimarron County, OK
    '40027': 'cleveland2024', #Cleveland County, OK
    '40029': 'coal2024', #Coal County, OK
    '40031': 'comanche2024', #Comanche County, OK
    '40033': 'cotton2024', #Cotton County, OK
    '40035': 'craig2024', #Craig County, OK
    '40037': 'creek2024', #Creek County, OK
    '40039': 'custer2024', #Custer County, OK
    '40041': 'delaware2024', #Delaware County, OK
    '40043': 'dewey2024', #Dewey County, OK
    '40045': 'ellis2024', #Ellis County, OK
    '40047': 'garfield2024', #Garfield County, OK
    '40049': 'garvin2024', #Garvin County, OK
    '40051': 'grady2024', #Grady County, OK
    '40053': 'grant2024', #Grant County, OK
    '40055': 'greer2024', #Greer County, OK
    '40057': 'harmon2024', #Harmon County, OK
    '40059': 'harper2024', #Harper County, OK
    '40061': 'haskell2024', #Haskell County, OK
    '40063': 'hughes2024', #Hughes County, OK
    '40065': 'jackson2024', #Jackson County, OK
    '40067': 'jefferson2024', #Jefferson County, OK
    '40069': 'johnston2024', #Johnston County, OK
    '40071': 'kay2024', #Kay County, OK
    '40073': 'kingfisher2024', #Kingfisher County, OK
    '40075': 'kiowa2024', #Kiowa County, OK
    '40077': 'latimer2024', #Latimer County, OK
    '40079': 'le flore2024', #Le Flore County, OK
    '40081': 'lincoln2024', #Lincoln County, OK
    '40083': 'logan2024', #Logan County, OK
    '40085': 'love2024', #Love County, OK
    '40087': 'mcclain2024', #McClain County, OK
    '40089': 'mccurtain2024', #McCurtain County, OK
    '40091': 'mcintosh2024', #McIntosh County, OK
    '40093': 'major2024', #Major County, OK
    '40095': 'marshall2024', #Marshall County, OK
    '40097': 'mayes2024', #Mayes County, OK
    '40099': 'murray2024', #Murray County, OK
    '40101': 'muskogee2024', #Muskogee County, OK
    '40103': 'noble2024', #Noble County, OK
    '40105': 'nowata2024', #Nowata County, OK
    '40107': 'okfuskee2024', #Okfuskee County, OK
    '40109': 'oklahoma2024', #Oklahoma County, OK
    '40111': 'okmulgee2024', #Okmulgee County, OK
    '40113': 'osage2024', #Osage County, OK
    '40115': 'ottawa2024', #Ottawa County, OK
    '40117': 'pawnee2024', #Pawnee County, OK
    '40119': 'payne2024', #Payne County, OK
    '40121': 'pittsburg2024', #Pittsburg County, OK
    '40123': 'pontotoc2024', #Pontotoc County, OK
    '40125': 'pottawatomie2024', #Pottawatomie County, OK
    '40127': 'pushmataha2024', #Pushmataha County, OK
    '40129': 'roger mills2024', #Roger Mills County, OK
    '40131': 'rogers2024', #Rogers County, OK
    '40133': 'seminole2024', #Seminole County, OK
    '40135': 'sequoyah2024', #Sequoyah County, OK
    '40137': 'stephens2024', #Stephens County, OK
    '40139': 'texas2024', #Texas County, OK
    '40141': 'tillman2024', #Tillman County, OK
    '40143': 'tulsa2024', #Tulsa County, OK
    '40145': 'wagoner2024', #Wagoner County, OK
    '40147': 'washington2024', #Washington County, OK
    '40149': 'washita2024', #Washita County, OK
    '40151': 'woods2024', #Woods County, OK
    '40153': 'woodward2024', #Woodward County, OK
    '41001': 'baker2024', #Baker County, OR
    '41003': 'benton2024', #Benton County, OR
    '41005': 'clackamas2024', #Clackamas County, OR
    '41007': 'clatsop2024', #Clatsop County, OR
    '41009': 'columbia2024', #Columbia County, OR
    '41011': 'coos2024', #Coos County, OR
    '41013': 'crook2024', #Crook County, OR
    '41015': 'curry2024', #Curry County, OR
    '41017': 'deschutes2024', #Deschutes County, OR
    '41019': 'douglas2024', #Douglas County, OR
    '41021': 'gilliam2024', #Gilliam County, OR
    '41023': 'grant2024', #Grant County, OR
    '41025': 'harney2024', #Harney County, OR
    '41027': 'hood river2024', #Hood River County, OR
    '41029': 'jackson2024', #Jackson County, OR
    '41031': 'jefferson2024', #Jefferson County, OR
    '41033': 'josephine2024', #Josephine County, OR
    '41035': 'klamath2024', #Klamath County, OR
    '41037': 'lake2024', #Lake County, OR
    '41039': 'lane2024', #Lane County, OR
    '41041': 'lincoln2024', #Lincoln County, OR
    '41043': 'linn2024', #Linn County, OR
    '41045': 'malheur2024', #Malheur County, OR
    '41047': 'marion2024', #Marion County, OR
    '41049': 'morrow2024', #Morrow County, OR
    '41051': 'multnomah2024', #Multnomah County, OR
    '41053': 'polk2024', #Polk County, OR
    '41055': 'sherman2024', #Sherman County, OR
    '41057': 'tillamook2024', #Tillamook County, OR
    '41059': 'umatilla2024', #Umatilla County, OR
    '41061': 'union2024', #Union County, OR
    '41063': 'wallowa2024', #Wallowa County, OR
    '41065': 'wasco2024', #Wasco County, OR
    '41067': 'washington2024', #Washington County, OR
    '41069': 'wheeler2024', #Wheeler County, OR
    '41071': 'yamhill2024', #Yamhill County, OR
    '42001': 'adams2024', #Adams County, PA
    '42003': 'allegheny2024', #Allegheny County, PA
    '42005': 'armstrong2024', #Armstrong County, PA
    '42007': 'beaver2024', #Beaver County, PA
    '42009': 'bedford2024', #Bedford County, PA
    '42011': 'berks2024', #Berks County, PA
    '42013': 'blair2024', #Blair County, PA
    '42015': 'bradford2024', #Bradford County, PA
    '42017': 'bucks2024', #Bucks County, PA
    '42019': 'butler2024', #Butler County, PA
    '42021': 'cambria2024', #Cambria County, PA
    '42023': 'cameron2024', #Cameron County, PA
    '42025': 'carbon2024', #Carbon County, PA
    '42027': 'centre2024', #Centre County, PA
    '42029': 'chester2024', #Chester County, PA
    '42031': 'clarion2024', #Clarion County, PA
    '42033': 'clearfield2024', #Clearfield County, PA
    '42035': 'clinton2024', #Clinton County, PA
    '42037': 'columbia2024', #Columbia County, PA
    '42039': 'crawford2024', #Crawford County, PA
    '42041': 'cumberland2024', #Cumberland County, PA
    '42043': 'dauphin2024', #Dauphin County, PA
    '42045': 'delaware2024', #Delaware County, PA
    '42047': 'elk2024', #Elk County, PA
    '42049': 'erie2024', #Erie County, PA
    '42051': 'fayette2024', #Fayette County, PA
    '42053': 'forest2024', #Forest County, PA
    '42055': 'franklin2024', #Franklin County, PA
    '42057': 'fulton2024', #Fulton County, PA
    '42059': 'greene2024', #Greene County, PA
    '42061': 'huntingdon2024', #Huntingdon County, PA
    '42063': 'indiana2024', #Indiana County, PA
    '42065': 'jefferson2024', #Jefferson County, PA
    '42067': 'juniata2024', #Juniata County, PA
    '42069': 'lackawanna2024', #Lackawanna County, PA
    '42071': 'lancaster2024', #Lancaster County, PA
    '42073': 'lawrence2024', #Lawrence County, PA
    '42075': 'lebanon2024', #Lebanon County, PA
    '42077': 'lehigh2024', #Lehigh County, PA
    '42079': 'luzerne2024', #Luzerne County, PA
    '42081': 'lycoming2024', #Lycoming County, PA
    '42083': 'mckean2024', #McKean County, PA
    '42085': 'mercer2024', #Mercer County, PA
    '42087': 'mifflin2024', #Mifflin County, PA
    '42089': 'monroe2024', #Monroe County, PA
    '42091': 'montgomery2024', #Montgomery County, PA
    '42093': 'montour2024', #Montour County, PA
    '42095': 'northampton2024', #Northampton County, PA
    '42097': 'northumberland2024', #Northumberland County, PA
    '42099': 'perry2024', #Perry County, PA
    '42101': 'philadelphia2024', #Philadelphia County, PA
    '42103': 'pike2024', #Pike County, PA
    '42105': 'potter2024', #Potter County, PA
    '42107': 'schuylkill2024', #Schuylkill County, PA
    '42109': 'snyder2024', #Snyder County, PA
    '42111': 'somerset2024', #Somerset County, PA
    '42113': 'sullivan2024', #Sullivan County, PA
    '42115': 'susquehanna2024', #Susquehanna County, PA
    '42117': 'tioga2024', #Tioga County, PA
    '42119': 'union2024', #Union County, PA
    '42121': 'venango2024', #Venango County, PA
    '42123': 'warren2024', #Warren County, PA
    '42125': 'washington2024', #Washington County, PA
    '42127': 'wayne2024', #Wayne County, PA
    '42129': 'westmoreland2024', #Westmoreland County, PA
    '42131': 'wyoming2024', #Wyoming County, PA
    '42133': 'york2024', #York County, PA
    '44001': 'bristol2024', #Bristol County, RI
    '44003': 'kent2024', #Kent County, RI
    '44005': 'newport2024', #Newport County, RI
    '44007': 'providence2024', #Providence County, RI
    '44009': 'washington2024', #Washington County, RI
    '45001': 'abbeville2024', #Abbeville County, SC
    '45003': 'aiken2024', #Aiken County, SC
    '45005': 'allendale2024', #Allendale County, SC
    '45007': 'anderson2024', #Anderson County, SC
    '45009': 'bamberg2024', #Bamberg County, SC
    '45011': 'barnwell2024', #Barnwell County, SC
    '45013': 'beaufort2024', #Beaufort County, SC
    '45015': 'berkeley2024', #Berkeley County, SC
    '45017': 'calhoun2024', #Calhoun County, SC
    '45019': 'charleston2024', #Charleston County, SC
    '45021': 'cherokee2024', #Cherokee County, SC
    '45023': 'chester2024', #Chester County, SC
    '45025': 'chesterfield2024', #Chesterfield County, SC
    '45027': 'clarendon2024', #Clarendon County, SC
    '45029': 'colleton2024', #Colleton County, SC
    '45031': 'darlington2024', #Darlington County, SC
    '45033': 'dillon2024', #Dillon County, SC
    '45035': 'dorchester2024', #Dorchester County, SC
    '45037': 'edgefield2024', #Edgefield County, SC
    '45039': 'fairfield2024', #Fairfield County, SC
    '45041': 'florence2024', #Florence County, SC
    '45043': 'georgetown2024', #Georgetown County, SC
    '45045': 'greenville2024', #Greenville County, SC
    '45047': 'greenwood2024', #Greenwood County, SC
    '45049': 'hampton2024', #Hampton County, SC
    '45051': 'horry2024', #Horry County, SC
    '45053': 'jasper2024', #Jasper County, SC
    '45055': 'kershaw2024', #Kershaw County, SC
    '45057': 'lancaster2024', #Lancaster County, SC
    '45059': 'laurens2024', #Laurens County, SC
    '45061': 'lee2024', #Lee County, SC
    '45063': 'lexington2024', #Lexington County, SC
    '45065': 'mccormick2024', #McCormick County, SC
    '45067': 'marion2024', #Marion County, SC
    '45069': 'marlboro2024', #Marlboro County, SC
    '45071': 'newberry2024', #Newberry County, SC
    '45073': 'oconee2024', #Oconee County, SC
    '45075': 'orangeburg2024', #Orangeburg County, SC
    '45077': 'pickens2024', #Pickens County, SC
    '45079': 'richland2024', #Richland County, SC
    '45081': 'saluda2024', #Saluda County, SC
    '45083': 'spartanburg2024', #Spartanburg County, SC
    '45085': 'sumter2024', #Sumter County, SC
    '45087': 'union2024', #Union County, SC
    '45089': 'williamsburg2024', #Williamsburg County, SC
    '45091': 'york2024', #York County, SC
    '46003': 'aurora2024', #Aurora County, SD
    '46005': 'beadle2024', #Beadle County, SD
    '46007': 'bennett2024', #Bennett County, SD
    '46009': 'bon homme2024', #Bon Homme County, SD
    '46011': 'brookings2024', #Brookings County, SD
    '46013': 'brown2024', #Brown County, SD
    '46015': 'brule2024', #Brule County, SD
    '46017': 'buffalo2024', #Buffalo County, SD
    '46019': 'butte2024', #Butte County, SD
    '46021': 'campbell2024', #Campbell County, SD
    '46023': 'charles mix2024', #Charles Mix County, SD
    '46025': 'clark2024', #Clark County, SD
    '46027': 'clay2024', #Clay County, SD
    '46029': 'codington2024', #Codington County, SD
    '46031': 'corson2024', #Corson County, SD
    '46033': 'custer2024', #Custer County, SD
    '46035': 'davison2024', #Davison County, SD
    '46037': 'day2024', #Day County, SD
    '46039': 'deuel2024', #Deuel County, SD
    '46041': 'dewey2024', #Dewey County, SD
    '46043': 'douglas2024', #Douglas County, SD
    '46045': 'edmunds2024', #Edmunds County, SD
    '46047': 'fall river2024', #Fall River County, SD
    '46049': 'faulk2024', #Faulk County, SD
    '46051': 'grant2024', #Grant County, SD
    '46053': 'gregory2024', #Gregory County, SD
    '46055': 'haakon2024', #Haakon County, SD
    '46057': 'hamlin2024', #Hamlin County, SD
    '46059': 'hand2024', #Hand County, SD
    '46061': 'hanson2024', #Hanson County, SD
    '46063': 'harding2024', #Harding County, SD
    '46065': 'hughes2024', #Hughes County, SD
    '46067': 'hutchinson2024', #Hutchinson County, SD
    '46069': 'hyde2024', #Hyde County, SD
    '46071': 'jackson2024', #Jackson County, SD
    '46073': 'jerauld2024', #Jerauld County, SD
    '46075': 'jones2024', #Jones County, SD
    '46077': 'kingsbury2024', #Kingsbury County, SD
    '46079': 'lake2024', #Lake County, SD
    '46081': 'lawrence2024', #Lawrence County, SD
    '46083': 'lincoln2024', #Lincoln County, SD
    '46085': 'lyman2024', #Lyman County, SD
    '46087': 'mccook2024', #McCook County, SD
    '46089': 'mcpherson2024', #McPherson County, SD
    '46091': 'marshall2024', #Marshall County, SD
    '46093': 'meade2024', #Meade County, SD
    '46095': 'mellette2024', #Mellette County, SD
    '46097': 'miner2024', #Miner County, SD
    '46099': 'minnehaha2024', #Minnehaha County, SD
    '46101': 'moody2024', #Moody County, SD
    '46102': 'oglala lakota2024', #Oglala Lakota County, SD
    '46103': 'pennington2024', #Pennington County, SD
    '46105': 'perkins2024', #Perkins County, SD
    '46107': 'potter2024', #Potter County, SD
    '46109': 'roberts2024', #Roberts County, SD
    '46111': 'sanborn2024', #Sanborn County, SD
    '46115': 'spink2024', #Spink County, SD
    '46117': 'stanley2024', #Stanley County, SD
    '46119': 'sully2024', #Sully County, SD
    '46121': 'todd2024', #Todd County, SD
    '46123': 'tripp2024', #Tripp County, SD
    '46125': 'turner2024', #Turner County, SD
    '46127': 'union2024', #Union County, SD
    '46129': 'walworth2024', #Walworth County, SD
    '46135': 'yankton2024', #Yankton County, SD
    '46137': 'ziebach2024', #Ziebach County, SD
    '47001': 'anderson2024', #Anderson County, TN
    '47003': 'bedford2024', #Bedford County, TN
    '47005': 'benton2024', #Benton County, TN
    '47007': 'bledsoe2024', #Bledsoe County, TN
    '47009': 'blount2024', #Blount County, TN
    '47011': 'bradley2024', #Bradley County, TN
    '47013': 'campbell2024', #Campbell County, TN
    '47015': 'cannon2024', #Cannon County, TN
    '47017': 'carroll2024', #Carroll County, TN
    '47019': 'carter2024', #Carter County, TN
    '47021': 'cheatham2024', #Cheatham County, TN
    '47023': 'chester2024', #Chester County, TN
    '47025': 'claiborne2024', #Claiborne County, TN
    '47027': 'clay2024', #Clay County, TN
    '47029': 'cocke2024', #Cocke County, TN
    '47031': 'coffee2024', #Coffee County, TN
    '47033': 'crockett2024', #Crockett County, TN
    '47035': 'cumberland2024', #Cumberland County, TN
    '47037': 'davidson2024', #Davidson County, TN
    '47039': 'decatur2024', #Decatur County, TN
    '47041': 'dekalb2024', #DeKalb County, TN
    '47043': 'dickson2024', #Dickson County, TN
    '47045': 'dyer2024', #Dyer County, TN
    '47047': 'fayette2024', #Fayette County, TN
    '47049': 'fentress2024', #Fentress County, TN
    '47051': 'franklin2024', #Franklin County, TN
    '47053': 'gibson2024', #Gibson County, TN
    '47055': 'giles2024', #Giles County, TN
    '47057': 'grainger2024', #Grainger County, TN
    '47059': 'greene2024', #Greene County, TN
    '47061': 'grundy2024', #Grundy County, TN
    '47063': 'hamblen2024', #Hamblen County, TN
    '47065': 'hamilton2024', #Hamilton County, TN
    '47067': 'hancock2024', #Hancock County, TN
    '47069': 'hardeman2024', #Hardeman County, TN
    '47071': 'hardin2024', #Hardin County, TN
    '47073': 'hawkins2024', #Hawkins County, TN
    '47075': 'haywood2024', #Haywood County, TN
    '47077': 'henderson2024', #Henderson County, TN
    '47079': 'henry2024', #Henry County, TN
    '47081': 'hickman2024', #Hickman County, TN
    '47083': 'houston2024', #Houston County, TN
    '47085': 'humphreys2024', #Humphreys County, TN
    '47087': 'jackson2024', #Jackson County, TN
    '47089': 'jefferson2024', #Jefferson County, TN
    '47091': 'johnson2024', #Johnson County, TN
    '47093': 'knox2024', #Knox County, TN
    '47095': 'lake2024', #Lake County, TN
    '47097': 'lauderdale2024', #Lauderdale County, TN
    '47099': 'lawrence2024', #Lawrence County, TN
    '47101': 'lewis2024', #Lewis County, TN
    '47103': 'lincoln2024', #Lincoln County, TN
    '47105': 'loudon2024', #Loudon County, TN
    '47107': 'mcminn2024', #McMinn County, TN
    '47109': 'mcnairy2024', #McNairy County, TN
    '47111': 'macon2024', #Macon County, TN
    '47113': 'madison2024', #Madison County, TN
    '47115': 'marion2024', #Marion County, TN
    '47117': 'marshall2024', #Marshall County, TN
    '47119': 'maury2024', #Maury County, TN
    '47121': 'meigs2024', #Meigs County, TN
    '47123': 'monroe2024', #Monroe County, TN
    '47125': 'montgomery2024', #Montgomery County, TN
    '47127': 'moore2024', #Moore County, TN
    '47129': 'morgan2024', #Morgan County, TN
    '47131': 'obion2024', #Obion County, TN
    '47133': 'overton2024', #Overton County, TN
    '47135': 'perry2024', #Perry County, TN
    '47137': 'pickett2024', #Pickett County, TN
    '47139': 'polk2024', #Polk County, TN
    '47141': 'putnam2024', #Putnam County, TN
    '47143': 'rhea2024', #Rhea County, TN
    '47145': 'roane2024', #Roane County, TN
    '47147': 'robertson2024', #Robertson County, TN
    '47149': 'rutherford2024', #Rutherford County, TN
    '47151': 'scott2024', #Scott County, TN
    '47153': 'sequatchie2024', #Sequatchie County, TN
    '47155': 'sevier2024', #Sevier County, TN
    '47157': 'shelby2024', #Shelby County, TN
    '47159': 'smith2024', #Smith County, TN
    '47161': 'stewart2024', #Stewart County, TN
    '47163': 'sullivan2024', #Sullivan County, TN
    '47165': 'sumner2024', #Sumner County, TN
    '47167': 'tipton2024', #Tipton County, TN
    '47169': 'trousdale2024', #Trousdale County, TN
    '47171': 'unicoi2024', #Unicoi County, TN
    '47173': 'union2024', #Union County, TN
    '47175': 'van buren2024', #Van Buren County, TN
    '47177': 'warren2024', #Warren County, TN
    '47179': 'washington2024', #Washington County, TN
    '47181': 'wayne2024', #Wayne County, TN
    '47183': 'weakley2024', #Weakley County, TN
    '47185': 'white2024', #White County, TN
    '47187': 'williamson2024', #Williamson County, TN
    '47189': 'wilson2024', #Wilson County, TN
    '48001': 'anderson2024', #Anderson County, TX
    '48003': 'andrews2024', #Andrews County, TX
    '48005': 'angelina2024', #Angelina County, TX
    '48007': 'aransas2024', #Aransas County, TX
    '48009': 'archer2024', #Archer County, TX
    '48011': 'armstrong2024', #Armstrong County, TX
    '48013': 'atascosa2024', #Atascosa County, TX
    '48015': 'austin2024', #Austin County, TX
    '48017': 'bailey2024', #Bailey County, TX
    '48019': 'bandera2024', #Bandera County, TX
    '48021': 'bastrop2024', #Bastrop County, TX
    '48023': 'baylor2024', #Baylor County, TX
    '48025': 'bee2024', #Bee County, TX
    '48027': 'bell2024', #Bell County, TX
    '48029': 'bexar2024', #Bexar County, TX
    '48031': 'blanco2024', #Blanco County, TX
    '48033': 'borden2024', #Borden County, TX
    '48035': 'bosque2024', #Bosque County, TX
    '48037': 'bowie2024', #Bowie County, TX
    '48039': 'brazoria2024', #Brazoria County, TX
    '48041': 'brazos2024', #Brazos County, TX
    '48043': 'brewster2024', #Brewster County, TX
    '48045': 'briscoe2024', #Briscoe County, TX
    '48047': 'brooks2024', #Brooks County, TX
    '48049': 'brown2024', #Brown County, TX
    '48051': 'burleson2024', #Burleson County, TX
    '48053': 'burnet2024', #Burnet County, TX
    '48055': 'caldwell2024', #Caldwell County, TX
    '48057': 'calhoun2024', #Calhoun County, TX
    '48059': 'callahan2024', #Callahan County, TX
    '48061': 'cameron2024', #Cameron County, TX
    '48063': 'camp2024', #Camp County, TX
    '48065': 'carson2024', #Carson County, TX
    '48067': 'cass2024', #Cass County, TX
    '48069': 'castro2024', #Castro County, TX
    '48071': 'chambers2024', #Chambers County, TX
    '48073': 'cherokee2024', #Cherokee County, TX
    '48075': 'childress2024', #Childress County, TX
    '48077': 'clay2024', #Clay County, TX
    '48079': 'cochran2024', #Cochran County, TX
    '48081': 'coke2024', #Coke County, TX
    '48083': 'coleman2024', #Coleman County, TX
    '48085': 'collin2024', #Collin County, TX
    '48087': 'collingsworth2024', #Collingsworth County, TX
    '48089': 'colorado2024', #Colorado County, TX
    '48091': 'comal2024', #Comal County, TX
    '48093': 'comanche2024', #Comanche County, TX
    '48095': 'concho2024', #Concho County, TX
    '48097': 'cooke2024', #Cooke County, TX
    '48099': 'coryell2024', #Coryell County, TX
    '48101': 'cottle2024', #Cottle County, TX
    '48103': 'crane2024', #Crane County, TX
    '48105': 'crockett2024', #Crockett County, TX
    '48107': 'crosby2024', #Crosby County, TX
    '48109': 'culberson2024', #Culberson County, TX
    '48111': 'dallam2024', #Dallam County, TX
    '48113': 'dallas2024', #Dallas County, TX
    '48115': 'dawson2024', #Dawson County, TX
    '48117': 'deaf smith2024', #Deaf Smith County, TX
    '48119': 'delta2024', #Delta County, TX
    '48121': 'denton2024', #Denton County, TX
    '48123': 'dewitt2024', #DeWitt County, TX
    '48125': 'dickens2024', #Dickens County, TX
    '48127': 'dimmit2024', #Dimmit County, TX
    '48129': 'donley2024', #Donley County, TX
    '48131': 'duval2024', #Duval County, TX
    '48133': 'eastland2024', #Eastland County, TX
    '48135': 'ector2024', #Ector County, TX
    '48137': 'edwards2024', #Edwards County, TX
    '48139': 'ellis2024', #Ellis County, TX
    '48141': 'el paso2024', #El Paso County, TX
    '48143': 'erath2024', #Erath County, TX
    '48145': 'falls2024', #Falls County, TX
    '48147': 'fannin2024', #Fannin County, TX
    '48149': 'fayette2024', #Fayette County, TX
    '48151': 'fisher2024', #Fisher County, TX
    '48153': 'floyd2024', #Floyd County, TX
    '48155': 'foard2024', #Foard County, TX
    '48157': 'fort bend2024', #Fort Bend County, TX
    '48159': 'franklin2024', #Franklin County, TX
    '48161': 'freestone2024', #Freestone County, TX
    '48163': 'frio2024', #Frio County, TX
    '48165': 'gaines2024', #Gaines County, TX
    '48167': 'galveston2024', #Galveston County, TX
    '48169': 'garza2024', #Garza County, TX
    '48171': 'gillespie2024', #Gillespie County, TX
    '48173': 'glasscock2024', #Glasscock County, TX
    '48175': 'goliad2024', #Goliad County, TX
    '48177': 'gonzales2024', #Gonzales County, TX
    '48179': 'gray2024', #Gray County, TX
    '48181': 'grayson2024', #Grayson County, TX
    '48183': 'gregg2024', #Gregg County, TX
    '48185': 'grimes2024', #Grimes County, TX
    '48187': 'guadalupe2024', #Guadalupe County, TX
    '48189': 'hale2024', #Hale County, TX
    '48191': 'hall2024', #Hall County, TX
    '48193': 'hamilton2024', #Hamilton County, TX
    '48195': 'hansford2024', #Hansford County, TX
    '48197': 'hardeman2024', #Hardeman County, TX
    '48199': 'hardin2024', #Hardin County, TX
    '48201': 'harris2024', #Harris County, TX
    '48203': 'harrison2024', #Harrison County, TX
    '48205': 'hartley2024', #Hartley County, TX
    '48207': 'haskell2024', #Haskell County, TX
    '48209': 'hays2024', #Hays County, TX
    '48211': 'hemphill2024', #Hemphill County, TX
    '48213': 'henderson2024', #Henderson County, TX
    '48215': 'hidalgo2024', #Hidalgo County, TX
    '48217': 'hill2024', #Hill County, TX
    '48219': 'hockley2024', #Hockley County, TX
    '48221': 'hood2024', #Hood County, TX
    '48223': 'hopkins2024', #Hopkins County, TX
    '48225': 'houston2024', #Houston County, TX
    '48227': 'howard2024', #Howard County, TX
    '48229': 'hudspeth2024', #Hudspeth County, TX
    '48231': 'hunt2024', #Hunt County, TX
    '48233': 'hutchinson2024', #Hutchinson County, TX
    '48235': 'irion2024', #Irion County, TX
    '48237': 'jack2024', #Jack County, TX
    '48239': 'jackson2024', #Jackson County, TX
    '48241': 'jasper2024', #Jasper County, TX
    '48243': 'jeff davis2024', #Jeff Davis County, TX
    '48245': 'jefferson2024', #Jefferson County, TX
    '48247': 'jim hogg2024', #Jim Hogg County, TX
    '48249': 'jim wells2024', #Jim Wells County, TX
    '48251': 'johnson2024', #Johnson County, TX
    '48253': 'jones2024', #Jones County, TX
    '48255': 'karnes2024', #Karnes County, TX
    '48257': 'kaufman2024', #Kaufman County, TX
    '48259': 'kendall2024', #Kendall County, TX
    '48261': 'kenedy2024', #Kenedy County, TX
    '48263': 'kent2024', #Kent County, TX
    '48265': 'kerr2024', #Kerr County, TX
    '48267': 'kimble2024', #Kimble County, TX
    '48269': 'king2024', #King County, TX
    '48271': 'kinney2024', #Kinney County, TX
    '48273': 'kleberg2024', #Kleberg County, TX
    '48275': 'knox2024', #Knox County, TX
    '48277': 'lamar2024', #Lamar County, TX
    '48279': 'lamb2024', #Lamb County, TX
    '48281': 'lampasas2024', #Lampasas County, TX
    '48283': 'la salle2024', #La Salle County, TX
    '48285': 'lavaca2024', #Lavaca County, TX
    '48287': 'lee2024', #Lee County, TX
    '48289': 'leon2024', #Leon County, TX
    '48291': 'liberty2024', #Liberty County, TX
    '48293': 'limestone2024', #Limestone County, TX
    '48295': 'lipscomb2024', #Lipscomb County, TX
    '48297': 'live oak2024', #Live Oak County, TX
    '48299': 'llano2024', #Llano County, TX
    '48301': 'loving2024', #Loving County, TX
    '48303': 'lubbock2024', #Lubbock County, TX
    '48305': 'lynn2024', #Lynn County, TX
    '48307': 'mcculloch2024', #McCulloch County, TX
    '48309': 'mclennan2024', #McLennan County, TX
    '48311': 'mcmullen2024', #McMullen County, TX
    '48313': 'madison2024', #Madison County, TX
    '48315': 'marion2024', #Marion County, TX
    '48317': 'martin2024', #Martin County, TX
    '48319': 'mason2024', #Mason County, TX
    '48321': 'matagorda2024', #Matagorda County, TX
    '48323': 'maverick2024', #Maverick County, TX
    '48325': 'medina2024', #Medina County, TX
    '48327': 'menard2024', #Menard County, TX
    '48329': 'midland2024', #Midland County, TX
    '48331': 'milam2024', #Milam County, TX
    '48333': 'mills2024', #Mills County, TX
    '48335': 'mitchell2024', #Mitchell County, TX
    '48337': 'montague2024', #Montague County, TX
    '48339': 'montgomery2024', #Montgomery County, TX
    '48341': 'moore2024', #Moore County, TX
    '48343': 'morris2024', #Morris County, TX
    '48345': 'motley2024', #Motley County, TX
    '48347': 'nacogdoches2024', #Nacogdoches County, TX
    '48349': 'navarro2024', #Navarro County, TX
    '48351': 'newton2024', #Newton County, TX
    '48353': 'nolan2024', #Nolan County, TX
    '48355': 'nueces2024', #Nueces County, TX
    '48357': 'ochiltree2024', #Ochiltree County, TX
    '48359': 'oldham2024', #Oldham County, TX
    '48361': 'orange2024', #Orange County, TX
    '48363': 'palo pinto2024', #Palo Pinto County, TX
    '48365': 'panola2024', #Panola County, TX
    '48367': 'parker2024', #Parker County, TX
    '48369': 'parmer2024', #Parmer County, TX
    '48371': 'pecos2024', #Pecos County, TX
    '48373': 'polk2024', #Polk County, TX
    '48375': 'potter2024', #Potter County, TX
    '48377': 'presidio2024', #Presidio County, TX
    '48379': 'rains2024', #Rains County, TX
    '48381': 'randall2024', #Randall County, TX
    '48383': 'reagan2024', #Reagan County, TX
    '48385': 'real2024', #Real County, TX
    '48387': 'red river2024', #Red River County, TX
    '48389': 'reeves2024', #Reeves County, TX
    '48391': 'refugio2024', #Refugio County, TX
    '48393': 'roberts2024', #Roberts County, TX
    '48395': 'robertson2024', #Robertson County, TX
    '48397': 'rockwall2024', #Rockwall County, TX
    '48399': 'runnels2024', #Runnels County, TX
    '48401': 'rusk2024', #Rusk County, TX
    '48403': 'sabine2024', #Sabine County, TX
    '48405': 'san augustine2024', #San Augustine County, TX
    '48407': 'san jacinto2024', #San Jacinto County, TX
    '48409': 'san patricio2024', #San Patricio County, TX
    '48411': 'san saba2024', #San Saba County, TX
    '48413': 'schleicher2024', #Schleicher County, TX
    '48415': 'scurry2024', #Scurry County, TX
    '48417': 'shackelford2024', #Shackelford County, TX
    '48419': 'shelby2024', #Shelby County, TX
    '48421': 'sherman2024', #Sherman County, TX
    '48423': 'smith2024', #Smith County, TX
    '48425': 'somervell2024', #Somervell County, TX
    '48427': 'starr2024', #Starr County, TX
    '48429': 'stephens2024', #Stephens County, TX
    '48431': 'sterling2024', #Sterling County, TX
    '48433': 'stonewall2024', #Stonewall County, TX
    '48435': 'sutton2024', #Sutton County, TX
    '48437': 'swisher2024', #Swisher County, TX
    '48439': 'tarrant2024', #Tarrant County, TX
    '48441': 'taylor2024', #Taylor County, TX
    '48443': 'terrell2024', #Terrell County, TX
    '48445': 'terry2024', #Terry County, TX
    '48447': 'throckmorton2024', #Throckmorton County, TX
    '48449': 'titus2024', #Titus County, TX
    '48451': 'tom green2024', #Tom Green County, TX
    '48453': 'travis2024', #Travis County, TX
    '48455': 'trinity2024', #Trinity County, TX
    '48457': 'tyler2024', #Tyler County, TX
    '48459': 'upshur2024', #Upshur County, TX
    '48461': 'upton2024', #Upton County, TX
    '48463': 'uvalde2024', #Uvalde County, TX
    '48465': 'val verde2024', #Val Verde County, TX
    '48467': 'van zandt2024', #Van Zandt County, TX
    '48469': 'victoria2024', #Victoria County, TX
    '48471': 'walker2024', #Walker County, TX
    '48473': 'waller2024', #Waller County, TX
    '48475': 'ward2024', #Ward County, TX
    '48477': 'washington2024', #Washington County, TX
    '48479': 'webb2024', #Webb County, TX
    '48481': 'wharton2024', #Wharton County, TX
    '48483': 'wheeler2024', #Wheeler County, TX
    '48485': 'wichita2024', #Wichita County, TX
    '48487': 'wilbarger2024', #Wilbarger County, TX
    '48489': 'willacy2024', #Willacy County, TX
    '48491': 'williamson2024', #Williamson County, TX
    '48493': 'wilson2024', #Wilson County, TX
    '48495': 'winkler2024', #Winkler County, TX
    '48497': 'wise2024', #Wise County, TX
    '48499': 'wood2024', #Wood County, TX
    '48501': 'yoakum2024', #Yoakum County, TX
    '48503': 'young2024', #Young County, TX
    '48505': 'zapata2024', #Zapata County, TX
    '48507': 'zavala2024', #Zavala County, TX
    '49001': 'beaver2024', #Beaver County, UT
    '49003': 'box elder2024', #Box Elder County, UT
    '49005': 'cache2024', #Cache County, UT
    '49007': 'carbon2024', #Carbon County, UT
    '49009': 'daggett2024', #Daggett County, UT
    '49011': 'davis2024', #Davis County, UT
    '49013': 'duchesne2024', #Duchesne County, UT
    '49015': 'emery2024', #Emery County, UT
    '49017': 'garfield2024', #Garfield County, UT
    '49019': 'grand2024', #Grand County, UT
    '49021': 'iron2024', #Iron County, UT
    '49023': 'juab2024', #Juab County, UT
    '49025': 'kane2024', #Kane County, UT
    '49027': 'millard2024', #Millard County, UT
    '49029': 'morgan2024', #Morgan County, UT
    '49031': 'piute2024', #Piute County, UT
    '49033': 'rich2024', #Rich County, UT
    '49035': 'salt lake2024', #Salt Lake County, UT
    '49037': 'san juan2024', #San Juan County, UT
    '49039': 'sanpete2024', #Sanpete County, UT
    '49041': 'sevier2024', #Sevier County, UT
    '49043': 'summit2024', #Summit County, UT
    '49045': 'tooele2024', #Tooele County, UT
    '49047': 'uintah2024', #Uintah County, UT
    '49049': 'utah2024', #Utah County, UT
    '49051': 'wasatch2024', #Wasatch County, UT
    '49053': 'washington2024', #Washington County, UT
    '49055': 'wayne2024', #Wayne County, UT
    '49057': 'weber2024', #Weber County, UT
    '50001': 'addison2024', #Addison County, VT
    '50003': 'bennington2024', #Bennington County, VT
    '50005': 'caledonia2024', #Caledonia County, VT
    '50007': 'chittenden2024', #Chittenden County, VT
    '50009': 'essex2024', #Essex County, VT
    '50011': 'franklin2024', #Franklin County, VT
    '50013': 'grand isle2024', #Grand Isle County, VT
    '50015': 'lamoille2024', #Lamoille County, VT
    '50017': 'orange2024', #Orange County, VT
    '50019': 'orleans2024', #Orleans County, VT
    '50021': 'rutland2024', #Rutland County, VT
    '50023': 'washington2024', #Washington County, VT
    '50025': 'windham2024', #Windham County, VT
    '50027': 'windsor2024', #Windsor County, VT
    '51001': 'accomack2024', #Accomack County, VA
    '51003': 'albemarle2024', #Albemarle County, VA
    '51005': 'alleghany2024', #Alleghany County, VA
    '51007': 'amelia2024', #Amelia County, VA
    '51009': 'amherst2024', #Amherst County, VA
    '51011': 'appomattox2024', #Appomattox County, VA
    '51013': 'arlington2024', #Arlington County, VA
    '51015': 'augusta2024', #Augusta County, VA
    '51017': 'bath2024', #Bath County, VA
    '51019': 'bedford2024', #Bedford County, VA
    '51021': 'bland2024', #Bland County, VA
    '51023': 'botetourt2024', #Botetourt County, VA
    '51025': 'brunswick2024', #Brunswick County, VA
    '51027': 'buchanan2024', #Buchanan County, VA
    '51029': 'buckingham2024', #Buckingham County, VA
    '51031': 'campbell2024', #Campbell County, VA
    '51033': 'caroline2024', #Caroline County, VA
    '51035': 'carroll2024', #Carroll County, VA
    '51036': 'charles city2024', #Charles City County, VA
    '51037': 'charlotte2024', #Charlotte County, VA
    '51041': 'chesterfield2024', #Chesterfield County, VA
    '51043': 'clarke2024', #Clarke County, VA
    '51045': 'craig2024', #Craig County, VA
    '51047': 'culpeper2024', #Culpeper County, VA
    '51049': 'cumberland2024', #Cumberland County, VA
    '51051': 'dickenson2024', #Dickenson County, VA
    '51053': 'dinwiddie2024', #Dinwiddie County, VA
    '51057': 'essex2024', #Essex County, VA
    '51059': 'fairfax2024', #Fairfax County, VA
    '51061': 'fauquier2024', #Fauquier County, VA
    '51063': 'floyd2024', #Floyd County, VA
    '51065': 'fluvanna2024', #Fluvanna County, VA
    '51067': 'franklin2024', #Franklin County, VA
    '51069': 'frederick2024', #Frederick County, VA
    '51071': 'giles2024', #Giles County, VA
    '51073': 'gloucester2024', #Gloucester County, VA
    '51075': 'goochland2024', #Goochland County, VA
    '51077': 'grayson2024', #Grayson County, VA
    '51079': 'greene2024', #Greene County, VA
    '51081': 'greensville2024', #Greensville County, VA
    '51083': 'halifax2024', #Halifax County, VA
    '51085': 'hanover2024', #Hanover County, VA
    '51087': 'henrico2024', #Henrico County, VA
    '51089': 'henry2024', #Henry County, VA
    '51091': 'highland2024', #Highland County, VA
    '51093': 'isle of wight2024', #Isle of Wight County, VA
    '51095': 'james city2024', #James City County, VA
    '51097': 'king and queen2024', #King and Queen County, VA
    '51099': 'king george2024', #King George County, VA
    '51101': 'king william2024', #King William County, VA
    '51103': 'lancaster2024', #Lancaster County, VA
    '51105': 'lee2024', #Lee County, VA
    '51107': 'loudoun2024', #Loudoun County, VA
    '51109': 'louisa2024', #Louisa County, VA
    '51111': 'lunenburg2024', #Lunenburg County, VA
    '51113': 'madison2024', #Madison County, VA
    '51115': 'mathews2024', #Mathews County, VA
    '51117': 'mecklenburg2024', #Mecklenburg County, VA
    '51119': 'middlesex2024', #Middlesex County, VA
    '51121': 'montgomery2024', #Montgomery County, VA
    '51125': 'nelson2024', #Nelson County, VA
    '51127': 'new kent2024', #New Kent County, VA
    '51131': 'northampton2024', #Northampton County, VA
    '51133': 'northumberland2024', #Northumberland County, VA
    '51135': 'nottoway2024', #Nottoway County, VA
    '51137': 'orange2024', #Orange County, VA
    '51139': 'page2024', #Page County, VA
    '51141': 'patrick2024', #Patrick County, VA
    '51143': 'pittsylvania2024', #Pittsylvania County, VA
    '51145': 'powhatan2024', #Powhatan County, VA
    '51147': 'prince edward2024', #Prince Edward County, VA
    '51149': 'prince george2024', #Prince George County, VA
    '51153': 'prince william2024', #Prince William County, VA
    '51155': 'pulaski2024', #Pulaski County, VA
    '51157': 'rappahannock2024', #Rappahannock County, VA
    '51159': 'richmond2024', #Richmond County, VA
    '51161': 'roanoke2024', #Roanoke County, VA
    '51163': 'rockbridge2024', #Rockbridge County, VA
    '51165': 'rockingham2024', #Rockingham County, VA
    '51167': 'russell2024', #Russell County, VA
    '51169': 'scott2024', #Scott County, VA
    '51171': 'shenandoah2024', #Shenandoah County, VA
    '51173': 'smyth2024', #Smyth County, VA
    '51175': 'southampton2024', #Southampton County, VA
    '51177': 'spotsylvania2024', #Spotsylvania County, VA
    '51179': 'stafford2024', #Stafford County, VA
    '51181': 'surry2024', #Surry County, VA
    '51183': 'sussex2024', #Sussex County, VA
    '51185': 'tazewell2024', #Tazewell County, VA
    '51187': 'warren2024', #Warren County, VA
    '51191': 'washington2024', #Washington County, VA
    '51193': 'westmoreland2024', #Westmoreland County, VA
    '51195': 'wise2024', #Wise County, VA
    '51197': 'wythe2024', #Wythe County, VA
    '51199': 'york2024', #York County, VA
    '51510': 'alexandria city2024', #Alexandria City County, VA
    '51520': 'bristol city2024', #Bristol City County, VA
    '51530': 'buena vista city2024', #Buena Vista City County, VA
    '51540': 'charlottesville city2024', #Charlottesville City County, VA
    '51550': 'chesapeake city2024', #Chesapeake City County, VA
    '51570': 'colonial heights city2024', #Colonial Heights City County, VA
    '51580': 'covington city2024', #Covington City County, VA
    '51590': 'danville city2024', #Danville City County, VA
    '51595': 'emporia city2024', #Emporia City County, VA
    '51600': 'fairfax city2024', #Fairfax City County, VA
    '51610': 'falls church city2024', #Falls Church City County, VA
    '51620': 'franklin city2024', #Franklin City County, VA
    '51630': 'fredericksburg city2024', #Fredericksburg City County, VA
    '51640': 'galax city2024', #Galax City County, VA
    '51650': 'hampton city2024', #Hampton City County, VA
    '51660': 'harrisonburg city2024', #Harrisonburg City County, VA
    '51670': 'hopewell city2024', #Hopewell City County, VA
    '51678': 'lexington city2024', #Lexington City County, VA
    '51680': 'lynchburg city2024', #Lynchburg City County, VA
    '51683': 'manassas city2024', #Manassas City County, VA
    '51685': 'manassas park city2024', #Manassas Park City County, VA
    '51690': 'martinsville city2024', #Martinsville City County, VA
    '51700': 'newport news city2024', #Newport News City County, VA
    '51710': 'norfolk city2024', #Norfolk City County, VA
    '51720': 'norton city2024', #Norton City County, VA
    '51730': 'petersburg city2024', #Petersburg City County, VA
    '51735': 'poquoson city2024', #Poquoson City County, VA
    '51740': 'portsmouth city2024', #Portsmouth City County, VA
    '51750': 'radford city2024', #Radford City County, VA
    '51760': 'richmond city2024', #Richmond City County, VA
    '51770': 'roanoke city2024', #Roanoke City County, VA
    '51775': 'salem city2024', #Salem City County, VA
    '51790': 'staunton city2024', #Staunton City County, VA
    '51800': 'suffolk city2024', #Suffolk City County, VA
    '51810': 'virginia beach city2024', #Virginia Beach City County, VA
    '51820': 'waynesboro city2024', #Waynesboro City County, VA
    '51830': 'williamsburg city2024', #Williamsburg City County, VA
    '51840': 'winchester city2024', #Winchester City County, VA
    '53001': 'adams2024', #Adams County, WA
    '53003': 'asotin2024', #Asotin County, WA
    '53005': 'benton2024', #Benton County, WA
    '53007': 'chelan2024', #Chelan County, WA
    '53009': 'clallam2024', #Clallam County, WA
    '53011': 'clark2024', #Clark County, WA
    '53013': 'columbia2024', #Columbia County, WA
    '53015': 'cowlitz2024', #Cowlitz County, WA
    '53017': 'douglas2024', #Douglas County, WA
    '53019': 'ferry2024', #Ferry County, WA
    '53021': 'franklin2024', #Franklin County, WA
    '53023': 'garfield2024', #Garfield County, WA
    '53025': 'grant2024', #Grant County, WA
    '53027': 'grays harbor2024', #Grays Harbor County, WA
    '53029': 'island2024', #Island County, WA
    '53031': 'jefferson2024', #Jefferson County, WA
    '53033': 'king2024', #King County, WA
    '53035': 'kitsap2024', #Kitsap County, WA
    '53037': 'kittitas2024', #Kittitas County, WA
    '53039': 'klickitat2024', #Klickitat County, WA
    '53041': 'lewis2024', #Lewis County, WA
    '53043': 'lincoln2024', #Lincoln County, WA
    '53045': 'mason2024', #Mason County, WA
    '53047': 'okanogan2024', #Okanogan County, WA
    '53049': 'pacific2024', #Pacific County, WA
    '53051': 'pend oreille2024', #Pend Oreille County, WA
    '53053': 'pierce2024', #Pierce County, WA
    '53055': 'san juan2024', #San Juan County, WA
    '53057': 'skagit2024', #Skagit County, WA
    '53059': 'skamania2024', #Skamania County, WA
    '53061': 'snohomish2024', #Snohomish County, WA
    '53063': 'spokane2024', #Spokane County, WA
    '53065': 'stevens2024', #Stevens County, WA
    '53067': 'thurston2024', #Thurston County, WA
    '53069': 'wahkiakum2024', #Wahkiakum County, WA
    '53071': 'walla walla2024', #Walla Walla County, WA
    '53073': 'whatcom2024', #Whatcom County, WA
    '53075': 'whitman2024', #Whitman County, WA
    '53077': 'yakima2024', #Yakima County, WA
    '54001': 'barbour2024', #Barbour County, WV
    '54003': 'berkeley2024', #Berkeley County, WV
    '54005': 'boone2024', #Boone County, WV
    '54007': 'braxton2024', #Braxton County, WV
    '54009': 'brooke2024', #Brooke County, WV
    '54011': 'cabell2024', #Cabell County, WV
    '54013': 'calhoun2024', #Calhoun County, WV
    '54015': 'clay2024', #Clay County, WV
    '54017': 'doddridge2024', #Doddridge County, WV
    '54019': 'fayette2024', #Fayette County, WV
    '54021': 'gilmer2024', #Gilmer County, WV
    '54023': 'grant2024', #Grant County, WV
    '54025': 'greenbrier2024', #Greenbrier County, WV
    '54027': 'hampshire2024', #Hampshire County, WV
    '54029': 'hancock2024', #Hancock County, WV
    '54031': 'hardy2024', #Hardy County, WV
    '54033': 'harrison2024', #Harrison County, WV
    '54035': 'jackson2024', #Jackson County, WV
    '54037': 'jefferson2024', #Jefferson County, WV
    '54039': 'kanawha2024', #Kanawha County, WV
    '54041': 'lewis2024', #Lewis County, WV
    '54043': 'lincoln2024', #Lincoln County, WV
    '54045': 'logan2024', #Logan County, WV
    '54047': 'mcdowell2024', #McDowell County, WV
    '54049': 'marion2024', #Marion County, WV
    '54051': 'marshall2024', #Marshall County, WV
    '54053': 'mason2024', #Mason County, WV
    '54055': 'mercer2024', #Mercer County, WV
    '54057': 'mineral2024', #Mineral County, WV
    '54059': 'mingo2024', #Mingo County, WV
    '54061': 'monongalia2024', #Monongalia County, WV
    '54063': 'monroe2024', #Monroe County, WV
    '54065': 'morgan2024', #Morgan County, WV
    '54067': 'nicholas2024', #Nicholas County, WV
    '54069': 'ohio2024', #Ohio County, WV
    '54071': 'pendleton2024', #Pendleton County, WV
    '54073': 'pleasants2024', #Pleasants County, WV
    '54075': 'pocahontas2024', #Pocahontas County, WV
    '54077': 'preston2024', #Preston County, WV
    '54079': 'putnam2024', #Putnam County, WV
    '54081': 'raleigh2024', #Raleigh County, WV
    '54083': 'randolph2024', #Randolph County, WV
    '54085': 'ritchie2024', #Ritchie County, WV
    '54087': 'roane2024', #Roane County, WV
    '54089': 'summers2024', #Summers County, WV
    '54091': 'taylor2024', #Taylor County, WV
    '54093': 'tucker2024', #Tucker County, WV
    '54095': 'tyler2024', #Tyler County, WV
    '54097': 'upshur2024', #Upshur County, WV
    '54099': 'wayne2024', #Wayne County, WV
    '54101': 'webster2024', #Webster County, WV
    '54103': 'wetzel2024', #Wetzel County, WV
    '54105': 'wirt2024', #Wirt County, WV
    '54107': 'wood2024', #Wood County, WV
    '54109': 'wyoming2024', #Wyoming County, WV
    '55001': 'adams2024', #Adams County, WI
    '55003': 'ashland2024', #Ashland County, WI
    '55005': 'barron2024', #Barron County, WI
    '55007': 'bayfield2024', #Bayfield County, WI
    '55009': 'brown2024', #Brown County, WI
    '55011': 'buffalo2024', #Buffalo County, WI
    '55013': 'burnett2024', #Burnett County, WI
    '55015': 'calumet2024', #Calumet County, WI
    '55017': 'chippewa2024', #Chippewa County, WI
    '55019': 'clark2024', #Clark County, WI
    '55021': 'columbia2024', #Columbia County, WI
    '55023': 'crawford2024', #Crawford County, WI
    '55025': 'dane2024', #Dane County, WI
    '55027': 'dodge2024', #Dodge County, WI
    '55029': 'door2024', #Door County, WI
    '55031': 'douglas2024', #Douglas County, WI
    '55033': 'dunn2024', #Dunn County, WI
    '55035': 'eau claire2024', #Eau Claire County, WI
    '55037': 'florence2024', #Florence County, WI
    '55039': 'fond du lac2024', #Fond du Lac County, WI
    '55041': 'forest2024', #Forest County, WI
    '55043': 'grant2024', #Grant County, WI
    '55045': 'green2024', #Green County, WI
    '55047': 'green lake2024', #Green Lake County, WI
    '55049': 'iowa2024', #Iowa County, WI
    '55051': 'iron2024', #Iron County, WI
    '55053': 'jackson2024', #Jackson County, WI
    '55055': 'jefferson2024', #Jefferson County, WI
    '55057': 'juneau2024', #Juneau County, WI
    '55059': 'kenosha2024', #Kenosha County, WI
    '55061': 'kewaunee2024', #Kewaunee County, WI
    '55063': 'la crosse2024', #La Crosse County, WI
    '55065': 'lafayette2024', #Lafayette County, WI
    '55067': 'langlade2024', #Langlade County, WI
    '55069': 'lincoln2024', #Lincoln County, WI
    '55071': 'manitowoc2024', #Manitowoc County, WI
    '55073': 'marathon2024', #Marathon County, WI
    '55075': 'marinette2024', #Marinette County, WI
    '55077': 'marquette2024', #Marquette County, WI
    '55078': 'menominee2024', #Menominee County, WI
    '55079': 'milwaukee2024', #Milwaukee County, WI
    '55081': 'monroe2024', #Monroe County, WI
    '55083': 'oconto2024', #Oconto County, WI
    '55085': 'oneida2024', #Oneida County, WI
    '55087': 'outagamie2024', #Outagamie County, WI
    '55089': 'ozaukee2024', #Ozaukee County, WI
    '55091': 'pepin2024', #Pepin County, WI
    '55093': 'pierce2024', #Pierce County, WI
    '55095': 'polk2024', #Polk County, WI
    '55097': 'portage2024', #Portage County, WI
    '55099': 'price2024', #Price County, WI
    '55101': 'racine2024', #Racine County, WI
    '55103': 'richland2024', #Richland County, WI
    '55105': 'rock2024', #Rock County, WI
    '55107': 'rusk2024', #Rusk County, WI
    '55109': 'st. croix2024', #St. Croix County, WI
    '55111': 'sauk2024', #Sauk County, WI
    '55113': 'sawyer2024', #Sawyer County, WI
    '55115': 'shawano2024', #Shawano County, WI
    '55117': 'sheboygan2024', #Sheboygan County, WI
    '55119': 'taylor2024', #Taylor County, WI
    '55121': 'trempealeau2024', #Trempealeau County, WI
    '55123': 'vernon2024', #Vernon County, WI
    '55125': 'vilas2024', #Vilas County, WI
    '55127': 'walworth2024', #Walworth County, WI
    '55129': 'washburn2024', #Washburn County, WI
    '55131': 'washington2024', #Washington County, WI
    '55133': 'waukesha2024', #Waukesha County, WI
    '55135': 'waupaca2024', #Waupaca County, WI
    '55137': 'waushara2024', #Waushara County, WI
    '55139': 'winnebago2024', #Winnebago County, WI
    '55141': 'wood2024', #Wood County, WI
    '56001': 'albany2024', #Albany County, WY
    '56003': 'big horn2024', #Big Horn County, WY
    '56005': 'campbell2024', #Campbell County, WY
    '56007': 'carbon2024', #Carbon County, WY
    '56009': 'converse2024', #Converse County, WY
    '56011': 'crook2024', #Crook County, WY
    '56013': 'fremont2024', #Fremont County, WY
    '56015': 'goshen2024', #Goshen County, WY
    '56017': 'hot springs2024', #Hot Springs County, WY
    '56019': 'johnson2024', #Johnson County, WY
    '56021': 'laramie2024', #Laramie County, WY
    '56023': 'lincoln2024', #Lincoln County, WY
    '56025': 'natrona2024', #Natrona County, WY
    '56027': 'niobrara2024', #Niobrara County, WY
    '56029': 'park2024', #Park County, WY
    '56031': 'platte2024', #Platte County, WY
    '56033': 'sheridan2024', #Sheridan County, WY
    '56035': 'sublette2024', #Sublette County, WY
    '56037': 'sweetwater2024', #Sweetwater County, WY
    '56039': 'teton2024', #Teton County, WY
    '56041': 'uinta2024', #Uinta County, WY
    '56043': 'washakie2024', #Washakie County, WY
    '56045': 'weston2024', #Weston County, WY
	
 # Format: 'FIPS_CODE': 'password'	
}

# Master password for all counties
MASTER_PASSWORD = 'county_dashboard_2024'

# Initialize the Dash app
app = dash.Dash(__name__, suppress_callback_exceptions=True)
app.title = "County Sustainability Dashboard - Secure Access"

# Initialize the enhanced data provider
if ENHANCED_V2_AVAILABLE:
    try:
        provider = BigQueryRadarChartDataProvider(
            PROJECT_ID,
            DATASET_ID,
            'display_names.csv'
        )
        print(f"✅ Enhanced BigQuery data provider initialized (Stage {provider.stage}/3)")
        print(f"📝 Display names: {len(provider.display_names_map)} mappings loaded")
    except Exception as e:
        print(f"⚠️  Enhanced provider initialization failed: {e}")
        provider = None
        ENHANCED_V2_AVAILABLE = False
else:
    provider = None

def validate_county_access(county_fips, password):
    """Validate if the provided password allows access to the specified county"""
    if not county_fips or not password:
        return False, "Missing county or password parameter"
    
    # Check master password first
    if MASTER_PASSWORD and password == MASTER_PASSWORD:
        return True, "Access granted with master password"
    
    # Check county-specific password
    if county_fips in COUNTY_PASSWORDS:
        if password == COUNTY_PASSWORDS[county_fips]:
            return True, f"Access granted for county {county_fips}"
        else:
            return False, f"Invalid password for county {county_fips}"
    else:
        return False, f"County {county_fips} not configured for access"

def get_all_counties():
    """Get list of all counties from BigQuery"""
    if ENHANCED_V2_AVAILABLE and provider:
        try:
            counties_df = provider.get_all_counties()
            if not counties_df.empty:
                print(f"✅ Found {len(counties_df)} counties from BigQuery")
                return counties_df
        except Exception as e:
            print(f"⚠️  Failed to get counties: {e}")
    
    return pd.DataFrame(columns=['fips_code', 'county_name', 'state_code', 'state_name'])

def get_county_metrics(county_fips):
    """Get all metrics for a specific county from BigQuery"""
    if ENHANCED_V2_AVAILABLE and provider:
        try:
            county_info, structured_data = provider.get_county_metrics(county_fips)
            if not county_info.empty and structured_data:
                print(f"✅ Loaded data for county {county_fips}")
                return county_info, structured_data
        except Exception as e:
            print(f"❌ Failed to load county data: {e}")
    
    return pd.DataFrame(), {}

def get_submetric_details(county_fips, top_level, sub_category):
    """Get detailed metrics from BigQuery"""
    if ENHANCED_V2_AVAILABLE and provider:
        try:
            details_df = provider.get_submetric_details(county_fips, top_level, sub_category)
            return details_df
        except Exception as e:
            print(f"❌ Failed to load submetric details: {e}")
    
    return pd.DataFrame()

def create_access_denied_layout(error_message="Access Denied"):
    """Create layout for access denied scenarios"""
    return html.Div([
        html.Div([
            html.H1("🔒 Access Denied", className="text-3xl font-bold text-red-600 mb-4"),
            html.P(error_message, className="text-lg text-gray-700 mb-6"),
            html.Div([
                html.H3("How to Access:", className="text-xl font-semibold mb-3"),
                html.Ul([
                    html.Li("Contact your county administrator for the correct access URL"),
                    html.Li("Ensure you have the correct county code and password"),
                    html.Li("URL format: yourdomain.com/?county=XXXXX&key=password"),
                ], className="list-disc list-inside space-y-2 text-gray-600")
            ], className="bg-gray-50 p-4 rounded-lg"),
        ], className="max-w-md mx-auto bg-white p-8 rounded-lg shadow-lg mt-20")
    ], className="min-h-screen bg-gray-100 flex items-center justify-center")

def create_dashboard_layout(county_fips, county_info, structured_data):
    """Create the main dashboard layout for authenticated users"""
    county_name = f"{county_info.iloc[0]['county_name']}, {county_info.iloc[0]['state_code']}"
    
    # Get population
    population = None
    if ENHANCED_V2_AVAILABLE and provider:
        population = provider.get_county_population(county_fips)
    
    # Create initial radar chart
    initial_radar_fig = create_enhanced_radar_chart(structured_data, county_name, provider, county_fips)
    
    return html.Div([
        # Header - UPDATED
        html.Div([
            html.Div([
                html.H1(f"{county_name} Sustainability Dashboard", 
                        className="text-3xl font-bold text-gray-800"),
                html.Div([
                    html.Span("Population: ", className="text-lg text-gray-600 font-medium"),
                    html.Span(f"{population:,}" if population else "N/A", 
                             className="text-lg text-gray-800 font-bold")
                ], className="mt-2") if population else html.Div()
            ], className="text-center")
        ], className="bg-white p-6 rounded-lg shadow-md mb-6"),
        
        # Main content
        html.Div([
            # Radar chart section
            html.Div([
                dcc.Graph(
                    id='radar-chart',
                    figure=initial_radar_fig,
                    style={'height': '700px'}
                )
            ], className="bg-white p-6 rounded-lg shadow-md", style={'width': '65%'}),
            
            # Summary section
            html.Div([
                html.Div([
                    html.H3("Quick Stats", className="text-lg font-semibold mb-4"),
                    html.Div(id='summary-stats')
                ], className="bg-white p-4 rounded-lg shadow-md mb-4"),
                
                html.Div([
                    html.H3("Comparison Mode", className="text-lg font-semibold mb-4"),
                    html.Div([
                        html.Button(
                            "National Comparison", 
                            id='national-mode-btn',
                            className="w-full mb-2 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                        ),
                        html.Button(
                            "Compare with State", 
                            id='state-mode-btn',
                            className="w-full mb-2 px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
                        ),
                        html.Div(id='comparison-status', className="text-xs text-gray-600 mt-2")
                    ])
                ], className="bg-white p-4 rounded-lg shadow-md mb-4"),
                
                html.Div([
                    html.H3("Instructions", className="text-lg font-semibold mb-4"),
                    html.Ul([
                        html.Li("Click on radar chart points to see detailed metrics"),
                        html.Li("People (Purple), Prosperity (Yellow), Place (Green)"),
                        html.Li("Switch between National and State comparisons"),
                        html.Li("Hover for detailed information")
                    ], className="text-sm text-gray-600 space-y-1 list-disc list-inside")
                ], className="bg-white p-4 rounded-lg shadow-md")
            ], style={'width': '33%', 'marginLeft': '2%'})
        ], className="flex"),
        
        # Detail section
        html.Div([
            html.H2(id='detail-title', className="text-xl font-semibold mb-4", 
                   children="Click on a radar chart point to view detailed metrics"),
            dcc.Graph(id='detail-chart', figure=go.Figure())
        ], id='detail-section', className="bg-white p-6 rounded-lg shadow-md mt-6", 
           style={'display': 'none'}),
        
        # Data stores
        dcc.Store(id='county-data-store', data=structured_data),
        dcc.Store(id='selected-county-info', data={
            'county_name': county_info.iloc[0]['county_name'],
            'state_code': county_info.iloc[0]['state_code'],
            'fips': county_fips
        }),
        dcc.Store(id='comparison-mode-store', data='national'),
        dcc.Store(id='authentication-store', data={'authenticated': True, 'county_fips': county_fips}),
        dcc.Store(id='population-store', data=population)
        
    ], className="min-h-screen bg-gray-100 p-6 max-w-7xl mx-auto")

# Main App Layout
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    html.Div(id='main-content')
])

# Authentication and Main Layout Callback
@app.callback(
    Output('main-content', 'children'),
    [Input('url', 'search')]
)
def authenticate_and_display(url_search):
    """Main authentication callback"""
    if not url_search:
        return create_access_denied_layout("No access parameters provided")
    
    try:
        query_params = parse_qs(url_search.lstrip('?'))
        county_fips = query_params.get('county', [None])[0]
        password = query_params.get('key', [None])[0]
    except:
        return create_access_denied_layout("Invalid URL format")
    
    is_valid, message = validate_county_access(county_fips, password)
    
    if not is_valid:
        return create_access_denied_layout(f"Authentication failed: {message}")
    
    try:
        county_info, structured_data = get_county_metrics(county_fips)
        
        if county_info.empty:
            return create_access_denied_layout(f"No data found for county {county_fips}")
        
        if ENHANCED_V2_AVAILABLE and provider:
            provider.set_comparison_mode('national')
        
        print(f"✅ Authenticated access for county {county_fips}")
        return create_dashboard_layout(county_fips, county_info, structured_data)
        
    except Exception as e:
        print(f"❌ Error loading county data: {e}")
        return create_access_denied_layout(f"Error loading data: {str(e)}")

# Update county data based on comparison mode
@app.callback(
    [Output('county-data-store', 'data'),
     Output('selected-county-info', 'data')],
    [Input('comparison-mode-store', 'data')],
    [State('authentication-store', 'data')]
)
def update_county_data(comparison_mode, auth_data):
    """Update county data based on comparison mode"""
    if not auth_data or not auth_data.get('authenticated'):
        return {}, {}
    
    county_fips = auth_data.get('county_fips')
    if not county_fips:
        return {}, {}
    
    if ENHANCED_V2_AVAILABLE and provider:
        if comparison_mode == 'state':
            counties_df = get_all_counties()
            county_row = counties_df[counties_df['fips_code'] == county_fips]
            if not county_row.empty:
                state_code = county_row.iloc[0]['state_code']
                provider.set_comparison_mode('state', state_code)
        else:
            provider.set_comparison_mode('national')
    
    county_info, structured_data = get_county_metrics(county_fips)
    
    if county_info.empty:
        return {}, {}
    
    county_details = {
        'county_name': county_info.iloc[0]['county_name'],
        'state_code': county_info.iloc[0]['state_code'],
        'fips': county_fips
    }
    
    return structured_data, county_details

# Update radar chart
@app.callback(
    Output('radar-chart', 'figure'),
    [Input('county-data-store', 'data'),
     Input('selected-county-info', 'data')],
    [State('authentication-store', 'data')]
)
def update_radar_chart(county_data, county_info, auth_data):
    """Update radar chart"""
    if not auth_data or not auth_data.get('authenticated'):
        return go.Figure()
    
    if not county_data or not county_info:
        return go.Figure()
    
    county_name = f"{county_info['county_name']}, {county_info['state_code']}"
    county_fips = county_info['fips']
    return create_enhanced_radar_chart(county_data, county_name, provider, county_fips)

# Update comparison mode
@app.callback(
    Output('comparison-mode-store', 'data'),
    [Input('national-mode-btn', 'n_clicks'),
     Input('state-mode-btn', 'n_clicks')],
    [State('comparison-mode-store', 'data')]
)
def update_comparison_mode(national_clicks, state_clicks, current_mode):
    """Update comparison mode"""
    import dash
    ctx = dash.callback_context
    if not ctx.triggered:
        return current_mode
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if button_id == 'national-mode-btn':
        return 'national'
    elif button_id == 'state-mode-btn':
        return 'state'
    
    return current_mode

# Update summary stats
@app.callback(
    Output('summary-stats', 'children'),
    [Input('county-data-store', 'data'),
     Input('comparison-mode-store', 'data')]
)
def update_summary_stats(county_data, comparison_mode):
    """Update summary stats"""
    if not county_data:
        return "No data available"
    
    category_colors = {
        'People': '#5760a6',
        'Prosperity': '#c0b265',
        'Place': '#588f57'
    }
    
    stats_items = []
    for category in ['People', 'Prosperity', 'Place']:
        if category in county_data and county_data[category]:
            subcats = county_data[category]
            avg_score = round(sum(subcats.values()) / len(subcats), 1)
            color = category_colors[category]
            
            stats_items.append(
                html.Div([
                    html.Div([
                        html.Span(category.upper(), className="font-medium text-white text-sm"),
                    ], className="px-3 py-1 rounded", style={'backgroundColor': color}),
                    html.Span(f"{avg_score}%", className="text-lg font-bold", style={'color': color})
                ], className="flex justify-between items-center p-3 bg-gray-50 rounded mb-2")
            )
    
    return stats_items

# Handle radar chart clicks
@app.callback(
    [Output('detail-section', 'style'),
     Output('detail-title', 'children'),
     Output('detail-chart', 'figure')],
    [Input('radar-chart', 'clickData')],
    [State('selected-county-info', 'data')]
)
def handle_radar_click(clickData, county_info):
    """Handle radar chart clicks"""
    if not clickData or not county_info:
        return {'display': 'none'}, "", go.Figure()
    
    try:
        point_data = clickData['points'][0]
        custom_data = point_data.get('customdata', [])
        
        if len(custom_data) >= 2:
            top_level = custom_data[0]
            sub_category = custom_data[1]
            
            details_df = get_submetric_details(county_info['fips'], top_level, sub_category)
            
            if not details_df.empty:
                title = f"{sub_category} Metrics - {county_info['county_name']}, {county_info['state_code']}"
                detail_fig = create_detail_chart(details_df, title, provider.comparison_mode)
                
                return {'display': 'block'}, title, detail_fig
    
    except Exception as e:
        print(f"Error handling click: {e}")
    
    return {'display': 'none'}, "", go.Figure()

# Custom CSS
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

server = app.server

if __name__ == '__main__':
    print("\n🔒 SECURE COUNTY SUSTAINABILITY DASHBOARD - BIGQUERY VERSION")
    print("=" * 70)
    
    if ENHANCED_V2_AVAILABLE and provider:
        print(f"✅ Connected to BigQuery (Stage {provider.stage}/3)")
        print(f"   Project: {PROJECT_ID}")
        print(f"   Dataset: {DATASET_ID}")
    else:
        print("❌ BigQuery connection failed")
    
    print(f"\n📋 Access URL Format:")
    print(f"   http://localhost:8050/?county=01001&key=autauga2024")
    
    print(f"\n🌐 Starting secure dashboard on http://localhost:8050")
    print("=" * 70)
    
    app.run(debug=True, host='0.0.0.0', port=8050)
