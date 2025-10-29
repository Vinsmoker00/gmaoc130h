from __future__ import annotations

from datetime import date, timedelta
from io import StringIO
from typing import Dict, List
import csv


def _decode_tsv(raw: str) -> List[Dict[str, str]]:
    """Decode a TSV string that uses escaped tab characters."""
    stripped = raw.strip()
    decoded = stripped.replace("\\t", "\t").replace("\\n", "\n")
    reader = csv.DictReader(StringIO(decoded), delimiter="\t")
    rows: List[Dict[str, str]] = []
    for row in reader:
        cleaned = {key: value.strip() if isinstance(value, str) else value for key, value in row.items()}
        if any(cleaned.values()):
            rows.append(cleaned)
    return rows


AIRCRAFT_DATA = _decode_tsv(
    """
Matricule\tType\tPosition\tStatut
CN-AOC\tC-130H\t3BAFRA\tVM
CN-AOD\tC-130H\tBASG\tVM
CN-AOE\tC-130H\t3BAFRA\tVM
CN-AOF\tC-130H\t3BAFRA\tMOD
CN-AOG\tC-130H\t3BAFRA\tDisponible
CN-AOI\tC-130H\t3BAFRA\tATT VM
CN-AOJ\tC-130H\tBASG\tVM
CN-AOK\tC-130H\t3BAFRA\tATT VM
CN-AOL\tC-130H\t3BAFRA\tATT RVT
CN-AOM\tC-130H\t3BAFRA\tCHECK C + ATT RVT
CN-AON\tC-130H\t3BAFRA\tDisponible
CN-AOO\tC-130H\t3BAFRA\tDisponible
CN-AOP\tC-130H\t3BAFRA\tDisponible
CN-AOR\tC-130H\tBASG\tVM
CN-AOS\tC-130H\t3BAFRA\tCHECK B
"""
)


MATERIAL_DATA = _decode_tsv(
    """
Designation\tPN\tdotation\tstock\tavionne\tindispo att rpn\ten rpn\tlitige\treforme\tconsommation annuelle\tSN\tDA\tstatus DA
REGULATING VALVE\tREG-8585\t28\t59\t9\t5\t9\t1\t4\t16\tSN000-01\tDA000-01\tacceptée
REGULATING VALVE\tREG-2425\t32\t58\t17\t5\t6\t3\t1\t15\tSN000-02\tDA000-02\tbloquée
REGULATING VALVE\tREG-2060\t29\t37\t18\t5\t4\t2\t0\t11\tSN000-03\tDA000-03\tacceptée
REGULATING VALVE\tREG-1117\t22\t38\t7\t9\t1\t2\t3\t10\tSN000-04\tDA000-04\tinstance autorisation
REGULATING VALVE\tREG-7331\t19\t66\t6\t4\t4\t1\t4\t11\tSN000-05\tDA000-05\tbloquée
REGULATING VALVE\tREG-8963\t19\t41\t12\t1\t2\t1\t3\t7\tSN001-01\tDA001-01\tinstance autorisation
REGULATING VALVE\tREG-4288\t27\t42\t15\t0\t8\t2\t2\t11\tSN001-02\tDA001-02\tbloquée
REGULATING VALVE\tREG-3452\t20\t63\t11\t0\t6\t2\t1\t11\tSN001-03\tDA001-03\tbloquée
REGULATING VALVE\tREG-4859\t28\t51\t7\t8\t9\t1\t3\t13\tSN001-04\tDA001-04\tacceptée
REGULATING VALVE\tREG-5335\t41\t69\t17\t8\t8\t4\t4\t21\tSN001-05\tDA001-05\tbloquée
REGULATING VALVE\tREG-5480\t27\t39\t13\t6\t4\t2\t2\t13\tSN002-01\tDA002-01\trejetée
REGULATING VALVE\tREG-5608\t20\t65\t5\t2\t9\t4\t0\t10\tSN002-02\tDA002-02\trejetée
REGULATING VALVE\tREG-8691\t17\t34\t5\t0\t8\t1\t3\t10\tSN002-03\tDA002-03\tinstance autorisation
REGULATING VALVE\tREG-1659\t33\t51\t19\t6\t0\t4\t4\t19\tSN002-04\tDA002-04\tinstance autorisation
REGULATING VALVE\tREG-2642\t34\t63\t19\t3\t6\t2\t4\t22\tSN002-05\tDA002-05\trejetée
REGULATING VALVE\tREG-6553\t24\t57\t8\t7\t7\t1\t1\t10\tSN003-01\tDA003-01\tacceptée
REGULATING VALVE\tREG-6843\t25\t42\t7\t9\t6\t2\t1\t13\tSN003-02\tDA003-02\tbloquée
REGULATING VALVE\tREG-9843\t24\t63\t16\t0\t6\t0\t2\t11\tSN003-03\tDA003-03\trejetée
REGULATING VALVE\tREG-8546\t24\t63\t6\t7\t8\t1\t2\t14\tSN003-04\tDA003-04\tbloquée
REGULATING VALVE\tREG-1111\t18\t63\t8\t8\t0\t1\t1\t9\tSN003-05\tDA003-05\tinstance autorisation
REGULATING VALVE\tREG-4355\t22\t32\t11\t1\t5\t3\t2\t12\tSN003-06\tDA003-06\tacceptée
REGULATING VALVE\tREG-3282\t30\t50\t16\t6\t6\t2\t0\t17\tSN003-07\tDA003-07\trejetée
REGULATING VALVE\tREG-3145\t17\t46\t8\t0\t3\t2\t4\t7\tSN003-08\tDA003-08\trejetée
REGULATING VALVE\tREG-6590\t29\t33\t19\t6\t4\t0\t0\t16\tSN003-09\tDA003-09\tbloquée
REGULATING VALVE\tREG-6251\t20\t60\t10\t7\t1\t1\t1\t8\tSN004-01\tDA004-01\tbloquée
REGULATING VALVE\tREG-6715\t30\t37\t11\t9\t4\t3\t3\t15\tSN004-02\tDA004-02\trejetée
REGULATING VALVE\tREG-2480\t25\t66\t12\t8\t1\t1\t3\t16\tSN004-03\tDA004-03\trejetée
REGULATING VALVE\tREG-3085\t21\t40\t15\t2\t2\t1\t1\t13\tSN004-04\tDA004-04\tbloquée
REGULATING VALVE\tREG-6082\t20\t37\t10\t2\t4\t2\t2\t8\tSN005-01\tDA005-01\tacceptée
REGULATING VALVE\tREG-5823\t24\t58\t9\t5\t2\t4\t4\t15\tSN006\tDA006\tinstance autorisation
REGULATING VALVE\tREG-6112\t20\t41\t14\t0\t1\t1\t4\t9\tSN007\tDA007\tinstance autorisation
REGULATING VALVE\tREG-5840\t33\t47\t14\t9\t7\t1\t2\t17\tSN008-01\tDA008-01\trejetée
REGULATING VALVE\tREG-5123\t23\t61\t7\t7\t7\t1\t1\t12\tSN008-02\tDA008-02\tbloquée
REGULATING VALVE\tREG-3519\t21\t38\t16\t1\t2\t1\t1\t9\tSN008-03\tDA008-03\trejetée
REGULATING VALVE\tREG-5985\t22\t68\t5\t1\t9\t3\t4\t10\tSN008-04\tDA008-04\tbloquée
REGULATING VALVE\tREG-6399\t12\t57\t6\t2\t0\t1\t3\t7\tSN008-05\tDA008-05\trejetée
REGULATING VALVE\tREG-2664\t22\t67\t11\t4\t5\t1\t1\t10\tSN008-06\tDA008-06\tinstance autorisation
REGULATING VALVE\tREG-2808\t29\t34\t14\t9\t6\t0\t0\t15\tSN008-07\tDA008-07\tacceptée
REGULATING VALVE\tREG-5320\t37\t46\t19\t7\t5\t4\t2\t16\tSN008-08\tDA008-08\tacceptée
REGULATING VALVE\tREG-4432\t8\t36\t6\t0\t0\t0\t2\t5\tSN009-01\tDA009-01\tacceptée
REGULATING VALVE\tREG-1191\t29\t69\t8\t6\t9\t3\t3\t15\tSN009-02\tDA009-02\trejetée
REGULATING VALVE\tREG-2675\t29\t37\t19\t4\t0\t4\t2\t14\tSN009-03\tDA009-03\trejetée
REGULATING VALVE\tREG-8014\t33\t56\t19\t8\t4\t0\t2\t18\tSN009-04\tDA009-04\tbloquée
REGULATING VALVE\tREG-3660\t23\t38\t6\t7\t3\t3\t4\t12\tSN009-05\tDA009-05\tinstance autorisation
REGULATING VALVE\tREG-3979\t36\t41\t14\t7\t9\t3\t3\t22\tSN009-06\tDA009-06\tbloquée
REGULATING VALVE\tREG-5434\t18\t68\t8\t4\t6\t0\t0\t12\tSN009-07\tDA009-07\tacceptée
REGULATING VALVE\tREG-8232\t27\t64\t12\t6\t5\t1\t3\t14\tSN009-08\tDA009-08\tbloquée
REGULATING VALVE\tREG-9195\t34\t34\t17\t7\t7\t1\t2\t14\tSN010-01\tDA010-01\trejetée
REGULATING VALVE\tREG-4870\t20\t41\t8\t6\t1\t1\t4\t9\tSN010-02\tDA010-02\tinstance autorisation
REGULATING VALVE\tREG-2366\t27\t61\t17\t5\t4\t1\t0\t16\tSN010-03\tDA010-03\tbloquée
REGULATING VALVE\tREG-8910\t28\t42\t16\t7\t2\t0\t3\t14\tSN010-04\tDA010-04\tinstance autorisation
REGULATING VALVE\tREG-2159\t31\t70\t8\t7\t9\t3\t4\t18\tSN010-05\tDA010-05\tinstance autorisation
REGULATING VALVE\tREG-6072\t33\t61\t19\t8\t2\t3\t1\t21\tSN010-06\tDA010-06\tbloquée
REGULATING VALVE\tREG-6425\t16\t59\t6\t5\t4\t1\t0\t9\tSN011-01\tDA011-01\tacceptée
REGULATING VALVE\tREG-6912\t11\t57\t5\t1\t4\t0\t1\t7\tSN011-02\tDA011-02\tbloquée
REGULATING VALVE\tREG-8907\t28\t53\t17\t2\t1\t4\t4\t16\tSN012\tDA012\trejetée
REGULATING VALVE\tREG-8441\t19\t40\t8\t5\t4\t0\t2\t9\tSN013-01\tDA013-01\tbloquée
REGULATING VALVE\tREG-4989\t22\t48\t8\t7\t2\t4\t1\t13\tSN013-02\tDA013-02\tinstance autorisation
REGULATING VALVE\tREG-4475\t18\t60\t8\t2\t3\t1\t4\t7\tSN013-03\tDA013-03\trejetée
REGULATING VALVE\tREG-3643\t21\t51\t5\t1\t8\t4\t3\t14\tSN013-04\tDA013-04\tacceptée
REGULATING VALVE\tREG-9661\t27\t63\t18\t1\t6\t2\t0\t15\tSN013-05\tDA013-05\tbloquée
REGULATING VALVE\tREG-4789\t24\t35\t13\t6\t0\t1\t4\t12\tSN013-06\tDA013-06\tbloquée
REGULATING VALVE\tREG-1857\t25\t55\t5\t9\t4\t4\t3\t11\tSN014-01\tDA014-01\tbloquée
REGULATING VALVE\tREG-4703\t27\t32\t7\t9\t6\t1\t4\t17\tSN014-02\tDA014-02\tacceptée
REGULATING VALVE\tREG-5036\t26\t35\t19\t4\t3\t0\t0\t11\tSN014-03\tDA014-03\trejetée
REGULATING VALVE\tREG-5788\t20\t70\t8\t4\t6\t2\t0\t9\tSN015-01\tDA015-01\tinstance autorisation
REGULATING VALVE\tREG-9633\t19\t38\t6\t5\t8\t0\t0\t9\tSN015-02\tDA015-02\tbloquée
REGULATING VALVE\tREG-5197\t11\t60\t5\t2\t0\t3\t1\t7\tSN015-03\tDA015-03\tinstance autorisation
REGULATING VALVE\tREG-3218\t23\t64\t11\t1\t7\t3\t1\t9\tSN015-04\tDA015-04\tbloquée
REGULATING VALVE\tREG-2386\t30\t36\t18\t6\t5\t0\t1\t15\tSN015-05\tDA015-05\tbloquée
REGULATING VALVE\tREG-2773\t17\t53\t7\t8\t2\t0\t0\t9\tSN015-06\tDA015-06\tbloquée
REGULATING VALVE\tREG-5360\t25\t32\t16\t2\t6\t0\t1\t10\tSN015-07\tDA015-07\tinstance autorisation
REGULATING VALVE\tREG-3134\t27\t58\t17\t5\t0\t1\t4\t15\tSN016-01\tDA016-01\tacceptée
TEM CONT VV LOW LIMIT\tBYLB-51044\t22\t39\t14\t1\t3\t3\t1\t11\tSN016-02\tDA016-02\tacceptée
TEM CONT VV LOW LIMIT\t398648-1-1\t31\t47\t12\t9\t5\t1\t4\t13\tSN016-03\tDA016-03\trejetée
TEM CONT VV LOW LIMIT\tTEM-6794\t24\t62\t5\t9\t7\t0\t3\t16\tSN016-04\tDA016-04\tacceptée
TEM CONT VV LOW LIMIT\t398648-2-1\t28\t46\t13\t5\t6\t0\t4\t15\tSN016-05\tDA016-05\trejetée
TEM CONT VV LOW LIMIT\tBYLB-51044\t19\t39\t5\t3\t6\t1\t4\t9\tSN016-06\tDA016-06\trejetée
TEM CONT VV LOW LIMIT\t398648-1-1\t17\t68\t9\t1\t4\t0\t3\t10\tSN016-07\tDA016-07\tbloquée
TEM CONT VV LOW LIMIT\tTEM-3836\t23\t35\t13\t5\t1\t1\t3\t14\tSN016-08\tDA016-08\tbloquée
TEM CONT VV LOW LIMIT\tMOUVEMENT MATERIEL (REPARATION OU BON ETAT)\t27\t48\t11\t0\t9\t3\t4\t11\tSN016-09\tDA016-09\tbloquée
TEM CONT VV LOW LIMIT\tTEM-1216\t27\t45\t10\t7\t5\t4\t1\t13\tSN017\tDA017\tbloquée
TEM CONT VV LOW LIMIT\tPART NUMBER\t23\t69\t8\t1\t8\t4\t2\t15\tSN018-01\tDA018-01\tacceptée
TEM CONT VV LOW LIMIT\t398648-1-1\t21\t51\t11\t0\t8\t0\t2\t12\tSN018-02\tDA018-02\tinstance autorisation
TEM CONT VV LOW LIMIT\tTEM-7231\t25\t68\t17\t2\t1\t4\t1\t10\tSN018-03\tDA018-03\tinstance autorisation
TEM CONT VV LOW LIMIT\tTEM-9733\t30\t50\t19\t6\t2\t2\t1\t12\tSN018-04\tDA018-04\tacceptée
TEM CONT VV LOW LIMIT\tTEM-1306\t37\t36\t15\t8\t8\t3\t3\t20\tSN018-05\tDA018-05\tacceptée
TEM CONT VV LOW LIMIT\tTEM-1574\t20\t37\t10\t6\t0\t4\t0\t9\tSN018-06\tDA018-06\tacceptée
TEM CONT VV LOW LIMIT\tTEM-1398\t31\t63\t19\t5\t3\t1\t3\t19\tSN018-07\tDA018-07\tbloquée
TEM CONT VV LOW LIMIT\tTEM-3647\t20\t48\t12\t0\t3\t1\t4\t11\tSN019-01\tDA019-01\trejetée
TEM CONT VV LOW LIMIT\tTEM-4961\t25\t50\t15\t1\t8\t0\t1\t11\tSN019-02\tDA019-02\tbloquée
TEM CONT VV LOW LIMIT\tTEM-4057\t30\t37\t14\t8\t6\t0\t2\t20\tSN019-03\tDA019-03\tacceptée
TEM CONT VV LOW LIMIT\tTEM-2970\t19\t37\t11\t2\t3\t2\t1\t12\tSN019-04\tDA019-04\tinstance autorisation
TEM CONT VV LOW LIMIT\t398648-2-1\t28\t68\t13\t5\t6\t2\t2\t13\tSN019-05\tDA019-05\trejetée
TEM CONT VV LOW LIMIT\tBYLB51044\t26\t69\t13\t6\t3\t1\t3\t11\tSN019-06\tDA019-06\tbloquée
TEM CONT VV LOW LIMIT\t398648-1-1\t34\t37\t15\t9\t7\t3\t0\t15\tSN019-07\tDA019-07\tinstance autorisation
TEM CONT VV LOW LIMIT\tTEM-3728\t32\t52\t17\t9\t3\t0\t3\t19\tSN019-08\tDA019-08\tbloquée
TEM CONT VV LOW LIMIT\t398648-2-1\t22\t59\t8\t5\t5\t0\t4\t13\tSN020-01\tDA020-01\trejetée
TEM CONT VV LOW LIMIT\tTEM-7021\t8\t48\t6\t0\t0\t0\t2\t4\tSN021-01\tDA021-01\trejetée
TEM CONT VV LOW LIMIT\tTEM-2054\t25\t70\t16\t2\t1\t2\t4\t12\tSN021-02\tDA021-02\trejetée
"""
)

PERSONNEL_DATA = _decode_tsv(
    """
Nom\tPrénom\tGrade\tMatricule\tSituation Familiale\tAtelier\tStatus
Ouahbi\tOmar\tCPT\tMA-69742\tDivorcé\tMARS\trepos
El Mansouri\tSaid\tCPT\tMA-51777\tCélibataire\tDRS\tpermanence
El Amrani\tImad\tADJ\tMA-68746\tMarié\tRADIO\tcongé
El Othmani\tMehdi\tCCH\tMA-76275\tCélibataire\tMOTEUR\tpermanence
El Othmani\tYassine\tCCH\tMA-99946\tDivorcé\tDRS\tautres
Ouahbi\tKarim\tS/LT\tMA-69041\tDivorcé\tDRS\tmalade
Bouazza\tMehdi\tSGT\tMA-37447\tDivorcé\tMARS\ten site
Chakiri\tSoufiane\tCPL\tMA-95109\tMarié\tFUEL\tautres
Sbai\tAyoub\tS/LT\tMA-91247\tDivorcé\tS/S\ten site
Ouahbi\tImad\tLT\tMA-77032\tDivorcé\tAPG\tperma
Alaoui\tAmine\tS/LT\tMA-83684\tCélibataire\tFUEL\trepos
El Othmani\tMehdi\tLT\tMA-75368\tCélibataire\tNDI\ten site
El Fassi\tOmar\tCPL\tMA-34020\tDivorcé\tS/S\tmalade
Haddad\tHassan\tLT\tMA-28993\tMarié\tEQT/BORD\tperma
El Mansouri\tYoussef\tSGT/CH\tMA-80102\tMarié\tEQT/BORD\tmalade
Tazi\tTarik\tADJ\tMA-58403\tCélibataire\tMOTEUR\tperma
Lamrani\tAmine\tSCH\tMA-37076\tMarié\tHELICE\trepos
El Amrani\tOmar\tLT\tMA-17862\tDivorcé\tMOTEUR\trepos
Chakiri\tAyoub\tCPL\tMA-70149\tCélibataire\tAPG\tperma
Tazi\tAnass\tLT\tMA-57296\tMarié\tMOTEUR\ten site
El Othmani\tHamza\tCPT\tMA-50994\tDivorcé\tDRS\ten site
Tazi\tRachid\tCPL\tMA-26199\tCélibataire\tDRS\tcongé
Essaid\tKhalid\tCCH\tMA-74295\tCélibataire\tMOTEUR\tcongé
Tazi\tYoussef\tLT\tMA-10920\tCélibataire\tNDI\tperma
Bouazza\tMehdi\tSCH\tMA-19777\tCélibataire\tFUEL\ten site
El Mansouri\tMohamed\tLT\tMA-46762\tCélibataire\tMARS\tcongé
El Othmani\tYassine\tLT\tMA-22578\tCélibataire\tDRS\tmalade
Haddad\tOmar\tS/LT\tMA-33856\tMarié\tHELICE\tmalade
El Idrissi\tOmar\tCCH\tMA-46322\tMarié\tEQT/BORD\trepos
El Othmani\tAbdelilah\tCPT\tMA-58029\tCélibataire\tS/S\tmalade
Ait Lahcen\tAnass\tCPL\tMA-27277\tMarié\tMOTEUR\tperma
El Fassi\tNabil\tADJ/CH\tMA-86251\tMarié\tS/S\tpermanence
Essaid\tNabil\tCCH\tMA-75357\tDivorcé\tCHAUD\tmalade
Sbai\tAyoub\tADJ/CH\tMA-24101\tCélibataire\tDRS\tcongé
Bennani\tKarim\tCCH\tMA-98427\tCélibataire\tEQT/BORD\tcongé
El Fassi\tImad\tSCH\tMA-36159\tMarié\tAPG\tcongé
Tahiri\tImad\tADJ/CH\tMA-33225\tMarié\tCHAUD\trepos
El Idrissi\tKhalid\tLT\tMA-25045\tMarié\tCHAUD\trepos
El Idrissi\tNabil\tADJ\tMA-46287\tCélibataire\tMOTEUR\tpermanence
Ouahbi\tAnass\tADJ\tMA-15496\tDivorcé\tRADIO\tperma
El Amrani\tYoussef\tSCH\tMA-25650\tMarié\tMARS\ten site
Essaid\tYoussef\tCPT\tMA-74807\tCélibataire\tRADIO\tpermanence
El Fassi\tKhalid\tLT\tMA-65526\tDivorcé\tNDI\trepos
El Fassi\tKhalid\tADJ/CH\tMA-23773\tDivorcé\tHELICE\tperma
El Idrissi\tTarik\tSGT\tMA-85260\tCélibataire\tFUEL\tpermanence
Benjelloun\tMohamed\tLT\tMA-66949\tCélibataire\tS/S\tautres
Tazi\tAyoub\tCCH\tMA-24468\tDivorcé\tMARS\ten site
Essaid\tYoussef\tADJ/CH\tMA-31044\tMarié\tDRS\ten site
El Fassi\tImad\tCPT\tMA-53243\tMarié\tDRS\tautres
Alaoui\tAmine\tSGT\tMA-26435\tDivorcé\tS/S\tperma
El Ghazali\tNabil\tCCH\tMA-84211\tDivorcé\tFUEL\ten site
Essaid\tYoussef\tLT\tMA-65351\tCélibataire\tEQT/BORD\trepos
Haddad\tNabil\tADJ/CH\tMA-21345\tDivorcé\tAPG\ten site
Lamrani\tMehdi\tSGT\tMA-31584\tDivorcé\tRADIO\tperma
Alaoui\tRachid\tS/LT\tMA-70638\tDivorcé\tNDI\ten site
Tazi\tYassine\tLT\tMA-26347\tCélibataire\tDRS\tautres
El Othmani\tRachid\tCPL\tMA-45248\tCélibataire\tRADIO\tperma
El Ghazali\tKarim\tCPL\tMA-69789\tDivorcé\tHELICE\trepos
El Mansouri\tSoufiane\tSCH\tMA-50236\tMarié\tHELICE\tpermanence
Ouahbi\tAmine\tCCH\tMA-87595\tMarié\tHELICE\tcongé
El Fassi\tAyoub\tLT\tMA-55733\tDivorcé\tDRS\ten site
Tazi\tHassan\tSGT\tMA-67395\tCélibataire\tFUEL\tcongé
Lamrani\tMehdi\tCPL\tMA-84051\tMarié\tFUEL\ten site
Essaid\tAmine\tCCH\tMA-87081\tMarié\tAPG\tmalade
Berrada\tAyoub\tADJ/CH\tMA-93880\tMarié\tMOTEUR\tcongé
Tazi\tAyoub\tCPT\tMA-92627\tCélibataire\tHELICE\tperma
El Amrani\tSoufiane\tSCH\tMA-39064\tCélibataire\tFUEL\tpermanence
El Ghazali\tMohamed\tCPT\tMA-12039\tCélibataire\tDRS\tcongé
El Ghazali\tNabil\tSGT\tMA-76509\tDivorcé\tMARS\ten site
Essaid\tHamza\tCPL\tMA-37870\tCélibataire\tCHAUD\tautres
El Mansouri\tAnass\tS/LT\tMA-64235\tMarié\tCHAUD\tautres
Haddad\tMohamed\tS/LT\tMA-37949\tMarié\tHELICE\tcongé
Lamrani\tAyoub\tCCH\tMA-77713\tMarié\tRADIO\trepos
Sbai\tAyoub\tCPL\tMA-93971\tDivorcé\tMARS\tperma
Lamrani\tOmar\tCPL\tMA-79743\tDivorcé\tEQT/BORD\tperma
Haddad\tYoussef\tADJ\tMA-21107\tMarié\tHELICE\tautres
Ouahbi\tAbdelilah\tCPL\tMA-90130\tDivorcé\tMOTEUR\tpermanence
Bouazza\tKhalid\tSGT\tMA-56007\tDivorcé\tMARS\tautres
Tazi\tMehdi\tCCH\tMA-65669\tDivorcé\tHELICE\tcongé
Essaid\tKhalid\tCPT\tMA-73569\tCélibataire\tFUEL\ten site
Ouahbi\tKarim\tLT\tMA-78630\tDivorcé\tS/S\trepos
Essaid\tTarik\tSGT\tMA-68841\tCélibataire\tCHAUD\tmalade
Tazi\tOmar\tS/LT\tMA-44350\tDivorcé\tEQT/BORD\tcongé
Tazi\tKhalid\tSGT/CH\tMA-65031\tCélibataire\tMARS\tperma
Sbai\tAyoub\tSCH\tMA-76417\tCélibataire\tNDI\tautres
Ait Lahcen\tMohamed\tLT\tMA-65557\tMarié\tRADIO\tcongé
El Mansouri\tRachid\tADJ\tMA-47712\tMarié\tNDI\trepos
El Othmani\tYassine\tCPL\tMA-30168\tMarié\tHELICE\tautres
Lamrani\tYassine\tSGT\tMA-77266\tCélibataire\tDRS\trepos
El Mansouri\tYoussef\tSGT\tMA-90729\tDivorcé\tAPG\tperma
Sbai\tAmine\tADJ\tMA-49914\tMarié\tNDI\tperma
Essaid\tTarik\tCPT\tMA-38178\tCélibataire\tMARS\tautres
Benjelloun\tKarim\tCCH\tMA-29180\tCélibataire\tEQT/BORD\tmalade
Tazi\tKarim\tCPT\tMA-47937\tDivorcé\tS/S\tmalade
Tazi\tYassine\tLT\tMA-91309\tDivorcé\tS/S\tcongé
Benjelloun\tOmar\tSGT\tMA-83071\tDivorcé\tMARS\tmalade
El Fassi\tSaid\tADJ/CH\tMA-46929\tDivorcé\tDRS\tmalade
Haddad\tYoussef\tCPT\tMA-36661\tMarié\tS/S\trepos
El Idrissi\tSoufiane\tSGT\tMA-63969\tDivorcé\tMARS\tpermanence
Ait Lahcen\tOmar\tCPL\tMA-78396\tDivorcé\tMARS\trepos
"""
)

VISIT_TEMPLATES = [
    {"code": "CHECK A", "period_months": 9, "duration_days": 7},
    {"code": "CHECK B", "period_months": 18, "duration_days": 14},
    {"code": "CHECK C", "period_months": 36, "duration_days": 21},
    {"code": "TRIMESTRIELLE", "period_months": 3, "duration_days": 5},
    {"code": "SEMESTRIELLE", "period_months": 6, "duration_days": 10},
]


def generate_visit_schedule(total: int, start_date: date | None = None) -> List[Dict[str, str]]:
    """Generate deterministic maintenance visit data."""
    if start_date is None:
        start_date = date.today()
    visits: List[Dict[str, str]] = []
    for idx in range(total):
        template = VISIT_TEMPLATES[idx % len(VISIT_TEMPLATES)]
        aircraft = AIRCRAFT_DATA[idx % len(AIRCRAFT_DATA)]
        spacing = template["period_months"] * 30
        start = start_date - timedelta(days=spacing * (idx // len(VISIT_TEMPLATES) + 1))
        end = start + timedelta(days=template["duration_days"])
        status = "completed"
        if idx % 5 == 0:
            status = "ongoing"
        elif idx % 7 == 0:
            status = "planned"
        visits.append(
            {
                "name": f"{template['code']} {aircraft['Matricule']} #{idx + 1}",
                "aircraft": aircraft["Matricule"],
                "vp_type": template["code"],
                "status": status,
                "start_date": start,
                "end_date": end,
            }
        )
    return visits
