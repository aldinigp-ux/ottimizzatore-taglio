import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import io
import re

# Configurazione Pagina per Mobile
st.set_page_config(page_title="Ottimizzatore Taglio Paolo", layout="wide")

def calcola_e_disegna_web(lastra_w, lastra_h, lista_pezzi, sp_lama=4):
    pezzi_validi = []
    pezzi_scartati = []
    
    # 1. Filtro iniziale pezzi fuori misura
    for p in lista_pezzi:
        if (p['w'] <= lastra_w and p['h'] <= lastra_h) or \
           (p['h'] <= lastra_w and p['w'] <= lastra_h):
            pezzi_validi.append(p)
        else:
            pezzi_scartati.append(p)

    # 2. Ordiniamo per dimensione maggiore
    pezzi_validi = sorted(pezzi_validi, key=lambda p: max(p['w'], p['h']), reverse=True)
    
    spazi_liberi = [{'x': 0, 'y': 0, 'w': lastra_w, 'h': lastra_h}]
    piazzati = []

    # 3. Ciclo di piazzamento (Il tuo algoritmo originale)
    for p in pezzi_validi:
        miglior_spazio_idx = -1
        miglior_orientamento = None
        min_width_waste = float('inf')

        for i, s in enumerate(spazi_liberi):
            for tw, th in [(p['w'], p['h']), (p['h'], p['w'])]:
                if tw <= s['w'] and th <= s['h']:
                    waste = s['w'] - tw
                    if waste < min_width_waste:
                        min_width_waste = waste
                        miglior_spazio_idx = i
                        miglior_orientamento = (tw, th)

        if miglior_spazio_idx != -1:
            tw, th = miglior_orientamento
            s_scelto = spazi_liberi.pop(miglior_spazio_idx)
            p['x'], p['y'], p['w'], p['h'] = s_scelto['x'], s_scelto['y'], tw, th
            piazzati.append(p.copy())
            
            gap_w = sp_lama if (s_scelto['x'] + tw + sp_lama) < lastra_w else 0
            gap_h = sp_lama if (s_scelto['y'] + th + sp_lama) < lastra_h else 0

            if s_scelto['w'] - (tw + gap_w) > 0:
                spazi_liberi.append({'x': s_scelto['x'] + tw + gap_w, 'y': s_scelto['y'], 'w': s_scelto['w'] - (tw + gap_w), 'h': s_scelto['h']})
            if s_scelto['h'] - (th + gap_h) > 0:
                spazi_liberi.append({'x': s_scelto['x'], 'y': s_scelto['y'] + th + gap_h, 'w': tw, 'h': s_scelto['h'] - (th + gap_h)})

    # 4. Calcolo statistiche
    area_usata = sum(p['w'] * p['h'] for p in piazzati)
    resa = (area_usata / (lastra_w * lastra_h)) * 100
    
    nomi_entrati = [p['label'] for p in piazzati]
    pezzi_fuori = []
    temp_nomi = nomi_entrati.copy()
    for p in lista_pezzi:
        if p['label'] in temp_nomi:
            temp_nomi.remove(p['label'])
        else:
            pezzi_fuori.append(p)

    riepilogo_mancanti = {}
    for p in pezzi_fuori:
        dim = f"{p['w']}x{p['h']}"
        riepilogo_mancanti[dim] = riepilogo_mancanti.get(dim, 0) + 1
    
    mancanti_testo = [f"{qta} pz da {dim}" for dim, qta in riepilogo_mancanti.items()]

    # 5. DISEGNO (Adattato per Streamlit)
    fig, (ax, ax_legenda) = plt.subplots(1, 2, figsize=(16, 7), gridspec_kw={'width_ratios': [5, 1]})
    
    ax.set_xlim(0, lastra_w)
    ax.set_ylim(0, lastra_h)
    ax.add_patch(patches.Rectangle((0,0), lastra_w, lastra_h, color='black', fill=False, lw=2))
    
    dati_legenda = []
    for r in piazzati:
        ax.add_patch(patches.Rectangle((r['x'], r['y']), r['w'], r['h'], facecolor='orange', edgecolor='black', alpha=0.7))
        etichetta_pulita = re.sub(r'\s*\(.*?\)', '', r['label'])
        ax.text(r['x']+r['w']/2, r['y']+r['h']/2, etichetta_pulita, ha='center', va='center', fontsize=7, fontweight='bold')
        dati_legenda.append([etichetta_pulita, f"{int(r['w'])}x{int(r['h'])}"])

    # Legenda
    ax_legenda.axis('off')
    dati_sorted = sorted(dati_legenda, key=lambda x: int(re.findall(r'\d+', x[0])[0]) if re.findall(r'\d+', x[0]) else 0)
    tabella = ax_legenda.table(cellText=dati_sorted, colLabels=['Pz', 'Dim.'], loc='upper center', cellLoc='center')
    tabella.auto_set_font_size(False)
    tabella.set_fontsize(8)
    tabella.scale(0.8, 1.1)

    info_testo = f"Resa: {resa:.2f}% | Piazzati: {len(piazzati)}/{len(lista_pezzi)}"
    ax.set_title(info_testo, color='red' if mancanti_testo else 'darkgreen', fontsize=12)
    ax.set_aspect('equal')
    
    return fig, info_testo, mancanti_testo

# --- INTERFACCIA STREAMLIT ---
st.title("✂️ Ottimizzatore Taglio v1.0")

with st.sidebar:
    st.header("⚙️ Parametri Lastra")
    l_w = st.number_input("Larghezza (W)", value=3500)
    l_h = st.number_input("Altezza (H)", value=2500)
    sp_l = st.number_input("Spessore Lama (mm)", value=4)
    
    st.header("📦 Lista Pezzi")
    st.info("Inserisci: Quantità, Larghezza, Altezza")
    input_testo = st.text_area("Esempio:\n1\n1200x900\n2\n500x400", "1\n1200x900\n45\n150x500")

# Parsing degli input
lista_input = [line.strip() for line in input_testo.split('\n') if line.strip()]
pezzi_da_ottimizzare = []
try:
    for i in range(0, len(lista_input), 2):
        qta = int(lista_input[i])
        dim = lista_input[i+1].lower().split('x')
        w_p, h_p = float(dim[0]), float(dim[1])
        for _ in range(qta):
            pezzi_da_ottimizzare.append({'w': w_p, 'h': h_p, 'label': f"Pz {len(pezzi_da_ottimizzare)+1} ({int(w_p)}x{int(h_p)})"})
except:
    st.error("⚠️ Formato pezzi non corretto!")

if st.button("🚀 CALCOLA OTTIMIZZAZIONE", use_container_width=True):
    if pezzi_da_ottimizzare:
        figura, stats, scarti = calcola_e_disegna_web(l_w, l_h, pezzi_da_ottimizzare, sp_l)
        
        st.success(stats)
        if scarti:
            st.warning(f"⚠️ NON ENTRANO: {', '.join(scarti)}")
            
        st.pyplot(figura)
        
        # Salvataggio PDF in memoria per il download
        buf = io.BytesIO()
        figura.savefig(buf, format="pdf", bbox_inches='tight')
        st.download_button(
            label="📩 SCARICA PDF PER OFFICINA",
            data=buf.getvalue(),
            file_name="Schema_Taglio_Web.pdf",
            mime="application/pdf",
            use_container_width=True
        )