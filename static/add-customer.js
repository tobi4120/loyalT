document.getElementById('add-customer-open-dialog').addEventListener('click', function(){
    document.querySelector('#overlay').style.display = 'flex';
    document.querySelector('.add-customer-modal').style.display = 'inline';
})

document.querySelector('.add-customer-close').addEventListener('click', function(){
    document.querySelector('#overlay').style.display = 'none';
    document.querySelector('.add-customer-modal').style.display = 'none';
})

