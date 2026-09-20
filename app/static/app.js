const thread = document.getElementById('thread');
const composer = document.getElementById('composer');
const input = document.getElementById('messageInput');
const typing = document.getElementById('typing');

const modal = document.getElementById('paymentModal');
const modalProductName = document.getElementById('modalProductName');
const modalAmount = document.getElementById('modalAmount');
const modalQuantity = document.getElementById('modalQuantity');
const modalPhone = document.getElementById('modalPhone');
const modalCancel = document.getElementById('modalCancel');
const modalConfirm = document.getElementById('modalConfirm');

const SESSION_KEY = 'talia_session_id';
let sessionId = localStorage.getItem(SESSION_KEY);
if (!sessionId) {
  sessionId = crypto.randomUUID();
  localStorage.setItem(SESSION_KEY, sessionId);
}

let activeProduct = null;

function formatFcfa(amount) {
  return new Intl.NumberFormat('fr-FR').format(amount) + ' FCFA';
}

function addMessage(role, text) {
  const el = document.createElement('div');
  el.className = `msg msg--${role}`;
  el.textContent = text;
  thread.appendChild(el);
  thread.scrollTop = thread.scrollHeight;
  return el;
}

function addProductCards(products) {
  if (!products || products.length === 0) return;

  const wrap = document.createElement('div');
  wrap.className = 'cards';

  products.forEach((p) => {
    const card = document.createElement('div');
    card.className = 'card';
    card.innerHTML = `
      <div class="card__top">
        <div>
          <p class="card__name">${p.name}</p>
          <span class="card__category">${p.category}</span>
        </div>
        <span class="card__price">${formatFcfa(p.price_fcfa)}</span>
      </div>
      <div class="card__bottom">
        <span class="card__stock">${p.stock} en stock</span>
        <button class="card__order" type="button">Commander</button>
      </div>
    `;
    card.querySelector('.card__order').addEventListener('click', () => openPaymentModal(p));
    wrap.appendChild(card);
  });

  thread.appendChild(wrap);
  thread.scrollTop = thread.scrollHeight;
}

async function sendMessage(message) {
  addMessage('user', message);
  typing.hidden = false;

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, message }),
    });
    const data = await res.json();
    typing.hidden = true;
    addMessage('bot', data.reply);
    addProductCards(data.products);
  } catch (err) {
    typing.hidden = true;
    addMessage('system', "Erreur de connexion au serveur Talia. Vérifie que le backend tourne.");
    console.error(err);
  }
}

composer.addEventListener('submit', (e) => {
  e.preventDefault();
  const value = input.value.trim();
  if (!value) return;
  input.value = '';
  sendMessage(value);
});

// ---------- Paiement ----------

function openPaymentModal(product) {
  activeProduct = product;
  modalProductName.textContent = product.name;
  modalQuantity.value = 1;
  modalPhone.value = '';
  updateModalAmount();
  modal.hidden = false;
}

function updateModalAmount() {
  const qty = Math.max(1, parseInt(modalQuantity.value || '1', 10));
  modalAmount.textContent = formatFcfa(activeProduct.price_fcfa * qty);
}

modalQuantity.addEventListener('input', updateModalAmount);

modalCancel.addEventListener('click', () => {
  modal.hidden = true;
});

modalConfirm.addEventListener('click', async () => {
  const provider = modal.querySelector('input[name="provider"]:checked').value;
  const phone = modalPhone.value.trim();
  const quantity = Math.max(1, parseInt(modalQuantity.value || '1', 10));

  if (!phone) {
    modalPhone.focus();
    return;
  }

  modalConfirm.disabled = true;
  modalConfirm.textContent = 'Envoi...';

  try {
    const res = await fetch('/api/payments/initiate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        product_id: activeProduct.id,
        quantity,
        provider,
        phone_number: phone,
      }),
    });
    const data = await res.json();
    modal.hidden = true;
    addMessage('system', `${data.message} · réf. ${data.payment_id}`);
  } catch (err) {
    addMessage('system', "Erreur lors de l'initiation du paiement.");
    console.error(err);
  } finally {
    modalConfirm.disabled = false;
    modalConfirm.textContent = 'Confirmer le paiement';
  }
});

// ---------- Message d'accueil ----------

addMessage(
  'bot',
  "Bonjour 👋 Je suis Talia, l'assistante commerciale d'ElectroCI. " +
  "Dis-moi ce que tu cherches — panneaux solaires, disjoncteurs, câblage, " +
  "onduleurs — et je te trouve le bon produit."
);
