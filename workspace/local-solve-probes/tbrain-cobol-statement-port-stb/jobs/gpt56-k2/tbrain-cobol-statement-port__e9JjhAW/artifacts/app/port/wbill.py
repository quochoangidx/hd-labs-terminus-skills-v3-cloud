#!/usr/bin/env python3
import sys, re
from decimal import Decimal, ROUND_HALF_UP, ROUND_HALF_EVEN, ROUND_FLOOR, ROUND_DOWN

TARIFFS = {
    'D': (10, 30, Decimal('1.2050'), Decimal('1.8575'), Decimal('2.4410'), Decimal('.3125')),
    'C': (50, 200, Decimal('1.1500'), Decimal('1.4025'), Decimal('1.6550'), Decimal('.9860')),
    'L': (10, 30, Decimal('1.2050'), Decimal('1.8575'), Decimal('2.4410'), Decimal('.3125')),
}

def q(v, places=2, mode=ROUND_HALF_UP):
    return Decimal(v).quantize(Decimal(1).scaleb(-places), rounding=mode)

def trunc(v, places=2):
    return q(v, places, ROUND_DOWN)

def nfmt(v, dec=2, commas=True):
    v = abs(Decimal(v))
    return (f'{v:,.{dec}f}' if commas else f'{v:.{dec}f}')

def z(v, width, dec=2, commas=True, blank_zero=False):
    if blank_zero and Decimal(v) == 0:
        return ' ' * width
    s = nfmt(v, dec, commas)
    return s.rjust(width)[-width:]

def signed_lead(v, width, dec=2, commas=True):
    v = Decimal(v)
    s = ('-' if v < 0 else '+') + nfmt(v, dec, commas)
    return s.rjust(width)[-width:]

def minus_lead(v, width, dec=2, commas=True):
    v = Decimal(v)
    s = (('-' if v < 0 else '') + nfmt(v, dec, commas))
    return s.rjust(width)[-width:]

def currency(v, width, dec=2, trailing_minus=False):
    v = Decimal(v)
    tail = '-' if trailing_minus and v < 0 else (' ' if trailing_minus else '')
    room = width - len(tail)
    num = nfmt(v, dec, True)
    # Floating currency symbol consumes one position of the edited field.
    s = '$' + num[-(room-1):]
    return s.rjust(room) + tail

def balance(v, width=14):
    v = Decimal(v)
    return nfmt(v, 2, True).rjust(width-2)[-(width-2):] + ('CR' if v < 0 else '  ')

def stars(v, width=10):
    return nfmt(v, 2, True).rjust(width, '*')[-width:]

def trailing_sign(v, width, currency_sign=False):
    v = Decimal(v)
    tail = '-' if v < 0 else ' '
    if currency_sign:
        return currency(v, width, 2, True)
    return nfmt(v, 2, True).rjust(width-1)[-(width-1):] + tail

def emit(out, s=''):
    out.write(s[:72].rstrip(' ').encode('ascii') + b'\n')

def recs(path):
    with open(path, 'rb') as f:
        for raw in f:
            raw = raw.rstrip(b'\n')
            if raw.endswith(b'\r'):
                raw = raw[:-1]
            yield raw[:80].decode('ascii').ljust(80)

def digits(s):
    return int(s)

def parse_numval(s):
    # TEST-NUMVAL forms documented by the runbook.
    m = re.fullmatch(r' *([+-]?) *([0-9]*(?:\.[0-9]*)?) *', s)
    if m and m.group(2) not in ('', '.'):
        v = Decimal(m.group(2))
        return -v if m.group(1) == '-' else v
    m = re.fullmatch(r' *([0-9]*(?:\.[0-9]*)?) *([+-]|CR|DB)? *', s)
    if m and m.group(1) not in ('', '.'):
        v = Decimal(m.group(1))
        return -v if m.group(2) in ('-', 'CR') else v
    return None

def main(readings, payments, output):
    lines = list(recs(readings))
    billed = rejected = credits = 0
    tot_units = 0
    tot_current = Decimal(0)
    tot_due = Decimal(0)
    tot_net = Decimal(0)
    accounts = []
    with open(output, 'wb') as out:
        pos = 0
        if lines and lines[0][0] == 'H':
            r = lines[0]; pos = 1
            date, region = r[1:9], r[9:29]
            dmy = date[6:8] + date[4:6] + date[0:4]
            emit(out, 'STATEMENTS FOR ' + region + ' DATED ' + dmy[0:2]+'/'+dmy[2:4]+'/'+dmy[4:8])
            emit(out)
        for r in lines[pos:]:
            if r[0] != 'C':
                continue
            acct, name, tariff = r[1:9], r[9:33], r[33]
            prev, curr, days = digits(r[34:40]), digits(r[40:46]), digits(r[46:49])
            arrears = Decimal((-1 if r[49]=='-' else 1) * digits(r[50:57])) / 100
            paid = Decimal(digits(r[57:64])) / 100
            reason = ''
            if tariff not in TARIFFS: reason = 'UNKNOWN TARIFF'
            elif days == 0: reason = 'NO BILLING DAYS'
            elif days > 120: reason = 'PERIOD TOO LONG'
            if reason:
                rejected += 1
                emit(out, 'REJECT ' + acct + ' ' + reason.ljust(20))
                emit(out)
                continue
            lim1, lim2, rate1, rate2, rate3, standrate = TARIFFS[tariff]
            units = curr-prev if curr >= prev else curr+1000000-prev
            l1 = q(Decimal(lim1*days)/30, 1)
            l2 = q(Decimal(lim2*days)/30, 1)
            if units > l1:
                b1 = l1
                if units > l2: b2, b3 = l2-l1, Decimal(units)-l2
                else: b2, b3 = Decimal(units)-l1, Decimal(0)
            else: b1, b2, b3 = Decimal(units), Decimal(0), Decimal(0)
            c1, c2, c3 = q(b1*rate1), q(b2*rate2), q(b3*rate3)
            usage = c1+c2+c3
            standing = q(Decimal(days)*standrate)
            discount = Decimal(0)
            if tariff == 'L':
                discount = trunc(usage*Decimal('.15'))
                usage -= discount
            net = usage+standing
            vat = q(net*Decimal('.05'))
            current = net+vat
            interest = q(arrears*Decimal('.015')) if arrears > 0 else Decimal(0)
            bal = current+arrears+interest-paid
            due = bal if bal > 0 else Decimal(0)
            carry = Decimal(0)
            if bal < 0:
                carry = q(bal*Decimal('.975'))
                credits += 1
            billed += 1
            accounts.append([acct, bal])
            tot_units += units; tot_current += current; tot_due += due; tot_net += bal
            upper = name.upper()
            cut = upper.find('  ')
            nameout = upper[:cut] if cut >= 0 else upper
            if not nameout.strip(): nameout = '(NO NAME ON FILE)'
            nameout = nameout.ljust(24)[:24]
            emit(out, 'ACCOUNT ****'+acct[4:8]+'  '+nameout+' TARIFF '+tariff)
            emit(out, 'READINGS '+str(prev).rjust(6)+' TO '+str(curr).rjust(6)+'  USAGE '+f'{units:,}'.rjust(9)+' OVER '+str(days).rjust(3)+' DAYS')
            emit(out, 'BANDS '+nfmt(b1,1,True).rjust(8)+' '+nfmt(b2,1,True).rjust(8)+' '+nfmt(b3,1,True).rjust(11))
            emit(out, 'USAGE CHARGE '+currency(usage,13)+'  STANDING'+currency(standing,10))
            emit(out, 'DISCOUNT '+z(discount,9,2,True,True)+'  VAT'+z(vat,10)+'  CURRENT'+currency(current,10))
            emit(out, 'ARREARS '+signed_lead(arrears,13)+'  INTEREST'+z(interest,9,2,True,True)+'  PAID'+z(paid,9))
            emit(out, 'BALANCE '+balance(bal)+'  AMOUNT DUE'+stars(due,10))
            if bal < 0: emit(out, 'CREDIT C/F '+currency(carry,11,2,True))
            emit(out)
        emit(out, 'ACCOUNTS BILLED '+str(billed).rjust(3)+'  REJECTED '+str(rejected).rjust(3)+'  CREDITS '+str(credits).rjust(3))
        emit(out, 'TOTAL UNITS '+f'{tot_units:,}'.rjust(11)+'  TOTAL CURRENT '+currency(tot_current,14))
        avg = q(tot_current/Decimal(billed)) if billed else Decimal(0)
        emit(out, 'TOTAL DUE '+currency(tot_due,14)+'  AVERAGE BILL '+currency(avg,13))
        emit(out, 'NET POSITION '+minus_lead(tot_net,14))
        emit(out)
        emit(out, 'PAYMENTS AND ADJUSTMENTS')
        applied = payrej = 0
        totpaid = Decimal(0); totother = Decimal(0)
        # UNSTRING receiving fields retain prior values when not overwritten.
        pl_acct=' '*8; pl_kind=' '*3; pl_amt=' '*16; pl_memo=' '*30
        for lineno, line in enumerate(recs(payments), 1):
            rawparts = line.split(';')
            fields = min(len(rawparts), 4)
            vals = rawparts[:4]
            acct_len = 0
            if len(vals) > 0:
                acct_len = min(len(vals[0]), 8)
                pl_acct = vals[0][:8].ljust(8)
            if len(vals) > 1: pl_kind = vals[1][:3].ljust(3)
            if len(vals) > 2: pl_amt = vals[2][:16].ljust(16)
            if len(vals) > 3: pl_memo = vals[3][:30].ljust(30)
            reason = ''
            amount0 = parse_numval(pl_amt)
            if fields < 3: reason='TOO FEW FIELDS'
            elif acct_len != 8: reason='BAD ACCOUNT'
            elif amount0 is None: reason='BAD AMOUNT'
            elif pl_kind not in ('PAY','ADJ','FEE','REF'): reason='BAD KIND'
            idx = next((i for i,a in enumerate(accounts) if a[0] == pl_acct), None) if not reason else None
            if not reason and idx is None: reason='NO SUCH ACCOUNT'
            if reason:
                payrej += 1
                emit(out, 'LINE '+str(lineno).rjust(3)+' REJECTED '+reason.ljust(20))
                continue
            if pl_kind == 'PAY':
                amt=q(amount0,2,ROUND_HALF_EVEN); accounts[idx][1]-=amt; totpaid+=amt
            elif pl_kind == 'ADJ':
                amt=q(amount0); accounts[idx][1]+=amt; totother+=amt
            elif pl_kind == 'FEE':
                amt=trunc(amount0); accounts[idx][1]+=amt; totother+=amt
                part=q(amt/3); rem=amt-part*3
            else:
                amt=q(amount0,2,ROUND_FLOOR); accounts[idx][1]+=amt; totother+=amt
            whole=amt.to_integral_value(rounding=ROUND_FLOOR)
            h=pl_memo.find('#')
            if h >= 0:
                pl_memo=pl_memo[:h+1]+''.join('X' if c.isdigit() else c for c in pl_memo[h+1:])
            applied += 1
            emit(out, pl_kind+' '+pl_acct+' '+minus_lead(amt,11)+' WHOLE '+minus_lead(whole,6,0,False)+' BAL '+balance(accounts[idx][1])+' '+pl_memo)
            if pl_kind == 'FEE':
                emit(out, '    FEE SPLIT 3X'+minus_lead(part,10)+' REMAINDER '+minus_lead(rem,5))
        emit(out, 'POSTED  '+str(applied).rjust(3)+'  REJECTED '+str(payrej).rjust(3)+'  PAID  '+currency(totpaid,14,2,True)+'  OTHER '+currency(totother,14,2,True))

if __name__ == '__main__':
    if len(sys.argv) != 4:
        raise SystemExit('usage: wbill.py <readings> <payments> <output>')
    main(*sys.argv[1:])
