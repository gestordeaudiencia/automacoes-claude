# Workflow GHL — Boleto gerado

**Objetivo:** confirmar emissão do boleto, mandar link + linha digitável, lembrar antes de vencer.

## Trigger

Tag `ev:boleto` adicionada ao contato.

## Steps

1. **Wait 3 minutes**
2. **Send Email**
   - **Subject:** `Seu boleto do {{contact.produto_nome}}`
   - **Body:**
     ```html
     <p>Oi {{contact.first_name}},</p>
     <p>Seu boleto de R$ {{contact.valor_brl}} para o <strong>{{contact.produto_nome}}</strong> foi emitido.
     Vencimento: {{contact.boleto_expiry}}.</p>
     <p><a href="{{contact.boleto_url}}" style="display:inline-block;background:#10b981;color:white;padding:12px 20px;border-radius:6px;text-decoration:none;">Abrir boleto</a></p>
     <p>Linha digitável:</p>
     <pre style="background:#f3f3f3;padding:12px;border-radius:6px;word-break:break-all;">{{contact.boleto_barcode}}</pre>
     ```

3. **Wait 1 day**
4. **If/Else** → "Has tag `ev:compra_aprovada`?"
   - Yes → End
   - No → continua
5. **Send Email** (lembrete véspera do vencimento — ajuste timing conforme prazo médio dos boletos teus)
   - **Subject:** `Lembrete: boleto vence em breve`
   - Body com mesma info, tom mais leve

6. Quando boleto vencer (cron externo ou regra de calendário): adicionar tag `boleto_expirado` → triga workflow `recovery-vencidos`

## Como montar

Mesmo padrão do `pix-gerado.md`. Trigger = tag `ev:boleto`.

**Cuidado especial com boleto:** prazo de vencimento varia (3-7 dias normalmente). Calibrar `Wait` baseado no que tu emite.
