def get_users_str(who, user):
    users = [name for name in who.split() if name.startswith('@')]
    if ' me ' in who:
        users.append(f'@{user}')
    return users


def rsplit(s, sep, i):
    splitted_text = str(s).split(sep)
    if i <= 0:
        return splitted_text
    result = [' '.join(splitted_text[:-i]), ]
    result.extend(splitted_text[-i:])
    return result


def get_when(aux):
    if aux.find('at ') > aux.find('in ') and aux.find('at ') > aux.find('every '):
        when = 'at ' + rsplit(aux, 'at ', 1)[1]
    elif aux.find('in ') > aux.find('at ') and aux.find('in ') > aux.find('every '):
        when = 'in ' + rsplit(aux, 'in ', 1)[1]
    elif aux.find('every ') > aux.find('in ') and aux.find('every ') > aux.find('at '):
        when = 'every ' + rsplit(aux, 'every ', 1)[1]
    else:
        when = ''

    return when
