# MS365-SharePoint MCP Server - Agent Instructions

**Version**: 1.0.0  
**Server**: ms365-sharepoint  
**Endpoint**: https://ms365-sharepoint.brainaihub.tech/mcp/sse

---

## 🎯 QUICK START

Questo MCP server ti permette di operare su Microsoft SharePoint tramite 6 tool.

**Autenticazione richiesta:**
1. **MCP_API_KEY** - per accedere al server (Bearer token)
2. **session_token** - per ogni tool (da TrustyVault via `trustyvault_verify_otp`)

**Flow tipico:**
```
User richiede operazione SharePoint
  ↓
1. Ottieni session_token (trustyvault_verify_otp)
2. Chiama tool SharePoint con session_token
3. Elabora risultato
```

---

## 🔧 TOOL DISPONIBILI (6)

### 1. sharepoint_list_sites
**Scopo**: Lista i siti SharePoint accessibili  
**Quando usarlo**: Prima operazione per esplorare SharePoint

**✨ AUTO-DISCOVERY**: Se nessun sito "seguito", cerca automaticamente con termini comuni (site, team, project, department, group).

**Parametri:**
- `session_token` (required) - Token TrustyVault
- `max_results` (optional, default=50) - Max siti da restituire (1-500)
- `search` (optional) - Query di ricerca specifica per nome sito

**Esempio:**
```json
{
  "session_token": "de1d1682-f81a-47f1-ab8c-21be0a0416af",
  "max_results": 10,
  "search": "engineering"
}
```

**Response:**
```json
{
  "success": true,
  "count": 3,
  "sites": [
    {
      "id": "contoso.sharepoint.com,abc123...",
      "name": "Engineering",
      "web_url": "https://contoso.sharepoint.com/sites/engineering",
      "description": "Engineering team site",
      "created_date_time": "2024-01-15T10:30:00Z"
    }
  ]
}
```

---

### 2. sharepoint_get_site
**Scopo**: Ottieni dettagli di un sito specifico  
**Quando usarlo**: Quando hai URL/ID di un sito

**Parametri:**
- `session_token` (required)
- `site_url` (optional) - URL completo (es: https://contoso.sharepoint.com/sites/engineering)
- `site_id` (optional) - Site ID alternativo

**Note**: Devi fornire `site_url` OR `site_id` (almeno uno)

**Esempio:**
```json
{
  "session_token": "de1d1682-...",
  "site_url": "https://contoso.sharepoint.com/sites/engineering"
}
```

---

### 3. sharepoint_list_lists
**Scopo**: Lista tutte le liste/librerie in un sito  
**Quando usarlo**: Dopo aver identificato un sito

**Parametri:**
- `session_token` (required)
- `site_url` (required) - URL del sito
- `include_hidden` (optional, default=false) - Includi liste nascoste

**Esempio:**
```json
{
  "session_token": "de1d1682-...",
  "site_url": "https://contoso.sharepoint.com/sites/engineering",
  "include_hidden": false
}
```

**Response:**
```json
{
  "success": true,
  "site_id": "contoso.sharepoint.com,abc...",
  "count": 5,
  "lists": [
    {
      "id": "tasks-list-id",
      "name": "Tasks",
      "display_name": "Team Tasks",
      "web_url": "https://contoso.sharepoint.com/sites/engineering/Lists/Tasks",
      "list_template": "genericList",
      "hidden": false
    }
  ]
}
```

---

### 4. sharepoint_get_list_items
**Scopo**: Leggi items da una lista  
**Quando usarlo**: Per visualizzare/cercare dati in una lista

**Parametri:**
- `session_token` (required)
- `site_url` (required)
- `list_id` (required) - ID o nome della lista
- `max_results` (optional, default=100) - Max items (1-500)
- `filter` (optional) - OData filter query (es: "Status eq 'Active'")
- `select` (optional) - Campi da selezionare (es: "Title,Status,DueDate")

**Esempio:**
```json
{
  "session_token": "de1d1682-...",
  "site_url": "https://contoso.sharepoint.com/sites/engineering",
  "list_id": "Tasks",
  "max_results": 20,
  "filter": "Status eq 'In Progress'",
  "select": "Title,Status,AssignedTo,DueDate"
}
```

**Response:**
```json
{
  "success": true,
  "count": 5,
  "items": [
    {
      "id": "1",
      "fields": {
        "Title": "Design new feature",
        "Status": "In Progress",
        "AssignedTo": "user@contoso.com",
        "DueDate": "2026-01-20"
      },
      "web_url": "https://contoso.sharepoint.com/...",
      "created_date_time": "2026-01-10T08:00:00Z"
    }
  ]
}
```

---

### 5. sharepoint_create_list_item
**Scopo**: Crea nuovo item in una lista  
**Quando usarlo**: Per aggiungere task, documenti, dati

**Parametri:**
- `session_token` (required)
- `site_url` (required)
- `list_id` (required)
- `fields` (required) - Dizionario con field:value

**Esempio:**
```json
{
  "session_token": "de1d1682-...",
  "site_url": "https://contoso.sharepoint.com/sites/engineering",
  "list_id": "Tasks",
  "fields": {
    "Title": "New task from AI",
    "Status": "Not Started",
    "Priority": "Normal",
    "AssignedTo": "user@contoso.com"
  }
}
```

**Response:**
```json
{
  "success": true,
  "item": {
    "id": "42",
    "fields": { ... },
    "web_url": "https://contoso.sharepoint.com/.../42_.000",
    "created_date_time": "2026-02-02T10:30:00Z"
  }
}
```

---

### 6. sharepoint_update_list_item
**Scopo**: Aggiorna item esistente  
**Quando usarlo**: Per modificare status, campi, ecc.

**Parametri:**
- `session_token` (required)
- `site_url` (required)
- `list_id` (required)
- `item_id` (required) - ID dell'item da aggiornare
- `fields` (required) - Solo i campi da aggiornare

**Esempio:**
```json
{
  "session_token": "de1d1682-...",
  "site_url": "https://contoso.sharepoint.com/sites/engineering",
  "list_id": "Tasks",
  "item_id": "42",
  "fields": {
    "Status": "Completed"
  }
}
```

---

## 🔄 PATTERN COMUNI

### Pattern 1: Esplora SharePoint
```
1. sharepoint_list_sites → ottieni lista siti
2. User sceglie un sito
3. sharepoint_list_lists → mostra liste disponibili
4. User sceglie una lista
5. sharepoint_get_list_items → visualizza contenuto
```

### Pattern 2: Cerca e aggiorna
```
1. sharepoint_get_list_items con filter → trova item specifico
2. sharepoint_update_list_item → aggiorna item trovato
```

### Pattern 3: Crea task/item
```
1. sharepoint_list_lists → verifica che la lista esista
2. (opzionale) sharepoint_get_list_items max_results=1 → vedi struttura campi
3. sharepoint_create_list_item → crea nuovo item
```

---

## ⚠️ GESTIONE ERRORI

### Errore: "session_expired"
**Causa**: Token TrustyVault scaduto (30 min lifetime)  
**Soluzione**: Richiama `trustyvault_verify_otp` per nuovo session_token

### Errore: "provider_not_configured"
**Causa**: User non ha configurato Microsoft 365 in TrustyVault  
**Soluzione**: Chiedi all'utente di aggiungere credenziali M365 in TrustyVault

### Errore: "Insufficient privileges"
**Causa**: Permessi SharePoint mancanti in Azure AD  
**Soluzione**: User/admin deve garantire permessi Sites.Read.All e Sites.ReadWrite.All

### Errore: "Authorization failed"
**Causa**: MCP_API_KEY invalida  
**Soluzione**: Verifica configurazione MCP client

### Errore: "Invalid filter"
**Causa**: Sintassi OData filter errata  
**Soluzione**: Usa sintassi OData corretta (es: "Status eq 'Active'" non "Status == 'Active'")

---

## 💡 BEST PRACTICES

### 1. Cache session_token
Se fai operazioni multiple, riusa lo stesso session_token (valido 30 min).

### 2. Usa site_url consistente
Mantieni formato completo URL: `https://tenant.sharepoint.com/sites/sitename`

### 3. Limita max_results
Per liste grandi, usa paginazione (max_results basso, poi filter per affinare).

### 4. Verifica success flag
Tutti i tool restituiscono `{"success": true/false}`. Controlla sempre prima di processare.

### 5. Gestisci campi dinamici
Struttura `fields` varia per lista. Prima query con `select` per capire campi disponibili.

### 6. URL encoding
SharePoint URLs possono avere spazi/caratteri speciali. Il server gestisce encoding automaticamente.

---

## 🚀 ESEMPIO COMPLETO

```python
# Scenario: User chiede "Trova task assegnati a me in Engineering site"

# Step 1: Ottieni session_token
session = await trustyvault_verify_otp(email="user@company.com", otp="123456")
token = session["session_token"]

# Step 2: Lista siti per trovare Engineering
sites = await sharepoint_list_sites(session_token=token, search="engineering")
eng_site = sites["sites"][0]["web_url"]

# Step 3: Lista liste nel sito
lists = await sharepoint_list_lists(session_token=token, site_url=eng_site)
tasks_list = next(l for l in lists["lists"] if l["name"] == "Tasks")

# Step 4: Filtra task assegnati a me
my_upn = "user@company.com"  # Estratto dal JWT
items = await sharepoint_get_list_items(
    session_token=token,
    site_url=eng_site,
    list_id=tasks_list["id"],
    filter=f"AssignedTo eq '{my_upn}'",
    select="Title,Status,DueDate"
)

# Step 5: Mostra risultati a user
for item in items["items"]:
    print(f"- {item['fields']['Title']} (Status: {item['fields']['Status']})")
```

---

## 📝 NOTE TECNICHE

### Token Caching
Il server caches access_token automaticamente (SQLite). Non serve gestirlo lato agent.

### Formato Date
SharePoint usa ISO 8601: `2026-02-02T10:30:00Z`

### OData Filters
Supporta operatori: `eq`, `ne`, `gt`, `lt`, `ge`, `le`, `and`, `or`, `not`  
Esempio: `"Status eq 'Active' and Priority eq 'High'"`

### Field Types
- Text: stringa normale
- Choice: valore da set predefinito
- DateTime: ISO 8601 string
- Person: email o UPN
- Number: integer o float

### Liste vs Librerie
- **Lista**: genericList, tasks, contacts, calendar
- **Libreria**: documentLibrary (file storage)

Entrambe usano gli stessi tool (sono tutte "lists" in Graph API).

---

## 🔗 RISORSE

- **Server**: https://ms365-sharepoint.brainaihub.tech
- **Health**: https://ms365-sharepoint.brainaihub.tech/health
- **Graph API Docs**: https://learn.microsoft.com/en-us/graph/api/resources/sharepoint
- **OData Filter**: https://learn.microsoft.com/en-us/graph/query-parameters#filter-parameter

---

**Versione**: 1.0.0  
**Ultimo aggiornamento**: 2026-02-02
