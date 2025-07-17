
import numpy as np

class cerebro_emb_pez_cebra:
    n_0 = np.float32(1.36) # 1.33 – 1.38	Agua, citoplasma, matriz extracelular
    Dn = np.float32(0.015) # ±0.01 – ±0.05	Heterogeneidad estructural (núcleo, orgánulos)
    l_s = np.float32(120e-6) # 	50 – 150 μm	Para medios como cerebro o piel
    alpha = np.float32(0.3) # mm*-1
    beta = np.float32(1e-11) # m/W
    n2 = np.float32(3e-20) # m²/W
