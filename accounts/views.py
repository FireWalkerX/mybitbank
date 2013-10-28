from connections import connector
import config
import forms
import generic
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _
from django.contrib.auth.decorators import login_required
from addressbook.models import savedAddress

current_section = 'accounts'

@login_required
def index(request):
    '''
    Handler for the accounts
    '''
    sections = generic.getSiteSections(current_section)
    
    accounts = generic.getAllAccounts(connector)
    transactions = generic.getTransactions(connector = connector, reverse_order = True)
    
    # find the first transaction for each account
    for account in accounts:
        for transaction in transactions:
            if account['name'] == transaction['account']:
                account['last_activity'] = generic.twitterizeDate(transaction['time'])
                account['address_count'] = len(account['addresses']) - 1
                break
        else:
            account['last_activity'] = "never"
    
    page_title = _("Accounts")
    context = {
               'globals': config.MainConfig['globals'], 
               'breadcrumbs': generic.buildBreadcrumbs(current_section, 'all'), 
               'system_errors': connector.errors,
               'page_title': page_title, 
               'page_sections': sections, 
               'accounts': accounts,
               'request': request,
               }
    return render(request, 'accounts/index.html', context)

@login_required
def add(request):
    '''
    Handler for the account create form
    '''
    form = forms.CreateAccountForm()
    context = getAddAccountFormContext(form=form)
    context['breadcrumbs'] = generic.buildBreadcrumbs(current_section, '', 'Create')
    return render(request, 'accounts/add.html', context)

def getAddAccountFormContext(account_name='', currency='btc', error=None, form=None):
    '''
    Provide a common context between the account view and create account view
    '''
    # get available currencies
    currencies_available = []
    currencies = connector.services.keys()
    for curr in currencies:
        currencies_available.append({'name': curr, 'title': connector.config[curr]['currency_name']})
        
    page_title = _("Create account")
    sections = generic.getSiteSections(current_section)
    context = {
               'globals': config.MainConfig['globals'], 
               'breadcrumbs': generic.buildBreadcrumbs(current_section, '', 'Create'),
               'page_sections': sections, 
               'page_title': page_title, 
               'currencies': currencies_available, 
               'account_name': account_name, 
               'currency': currency, 
               'selected_currency': currency, 
               'error_message': error,
               'form': form,
               }
    return context

@login_required
def create(request):
    '''
    Handler for POST of create account form
    '''
    
    # put default values
    new_account_name = ""
    currency = ""
    
    if request.method == 'POST': 
        
        # we have a POST request
        form = forms.CreateAccountForm(request.POST)
    
        if form.is_valid(): 
            new_account_name = form.cleaned_data['account_name']
            currency = form.cleaned_data['currency']
            
            # all ok, create account
            new_address = connector.getnewaddress(currency, new_account_name)
            return HttpResponseRedirect(reverse('accounts:index'))

    else:
        form = forms.CreateAccountForm()
    
    context = getAddAccountFormContext(account_name=new_account_name, currency=currency, form=form)
    return render(request, 'accounts/add.html', context)
    
@login_required        
def details(request, account_address="pipes"):
    '''
    Handler for the account details
    '''

    # add a list of pages in the view
    sections = generic.getSiteSections(current_section)
    
    # get account details
    account = connector.getaccountdetailsbyaddress(account_address)
    currency_symbol = generic.getCurrencySymbol(account['currency'])
    currency_name = connector.config[account['currency']]['currency_name']
    
    # get addressbook
    addressBookAddresses = savedAddress.objects.all()
    saved_addresses = {}
    for saved_address in addressBookAddresses:
        saved_addresses[saved_address.address] = saved_address.name
    print saved_addresses
    
    if account:
        # get transaction details
        transactions = generic.getTransactionsByAccount(connector, account['name'], account['currency'], reverse_order=True)
        for transaction in transactions:
            transaction['currency_symbol'] = generic.getCurrencySymbol(transaction['currency'].lower())
            if not transaction.get('details', {}).get('sender_address', False):
                    transaction['details']['sender_address'] = '(unknown)'
            
            # addressbook names and address resolution
            if transaction['category'] == 'move':
                transaction['otheraccount_address'] = connector.getaddressesbyaccount(transaction['otheraccount'], transaction['currency'])
            elif transaction['category'] == 'receive':
                transaction['source_address'] = transaction.get('details', {}).get('sender_address', '(no sender address)')
                transaction['addressbook_name'] = saved_addresses.get(transaction['source_address'], False)
            elif transaction['category'] == 'send':
                transaction['source_addresses'] = connector.getaddressesbyaccount(transaction['account'], transaction['currency'])
                print transaction
                print 
                transaction['addressbook_name'] = saved_addresses.get(transaction['address'], False)
                print transaction['addressbook_name']
                print 
                
            # use icons and colors to represent confirmations
            if transaction.get('confirmations', False) is not False:
                if transaction['confirmations'] <= config.MainConfig['globals']['confirmation_limit']:
                    transaction['status_icon'] = 'glyphicon-time'
                    transaction['status_color'] = '#DDD';
                    transaction['tooltip'] = transaction['confirmations']
                else:
                    transaction['status_icon'] = 'glyphicon-ok-circle'
                    transaction['status_color'] = '#1C9E3F';
                    transaction['tooltip'] = transaction['confirmations']
    else:
        account = {}
        account['name'] = _('no such account')
        transactions = []
    
    page_title = _("Account details for %s") % (account['name'] or account['alternative_name'])
    sender_address_tooltip_text = "This address has been calculated using the Input Script Signature. You should verify before using it."
    
    context = {
               'globals': config.MainConfig['globals'],
               'request': request,
               'system_errors': connector.errors,
               'breadcrumbs': generic.buildBreadcrumbs(current_section, '', account['name'] or account['alternative_name']), 
               'page_title': page_title, 
               'page_sections': sections, 
               'account': account,
               'transactions': transactions,
               'currency_name': currency_name,
               'currency_symbol': currency_symbol,
               'sender_address_tooltip_text': sender_address_tooltip_text,
               }
    
    return render(request, 'accounts/details.html', context)
    