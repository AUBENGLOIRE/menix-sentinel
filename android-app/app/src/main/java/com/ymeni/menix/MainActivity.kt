package com.ymeni.menix

import android.graphics.Color
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.ymeni.menix.databinding.ActivityMainBinding
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.launch

class MainActivity : AppCompatActivity() {

    private lateinit var b: ActivityMainBinding
    private var torchOn = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        b = ActivityMainBinding.inflate(layoutInflater)
        setContentView(b.root)

        // --- Boutons ---
        b.btnTorch.setOnClickListener {
            torchOn = !torchOn
            if (torchOn) TermuxBridge.torchOn(this) else TermuxBridge.torchOff(this)
            b.btnTorch.text = if (torchOn) "TORCHE: ON" else "TORCHE: OFF"
        }
        b.btnSos.setOnClickListener   { TermuxBridge.sos(this) }
        b.btnPhoto.setOnClickListener { TermuxBridge.photo(this) }
        b.btnStop.setOnClickListener  {
            torchOn = false
            b.btnTorch.text = "TORCHE: OFF"
            TermuxBridge.stop(this)
        }

        // --- Stream capteurs ---
        lifecycleScope.launch {
            SensorRepo.stream(1000).collectLatest { snap ->
                if (snap == null) {
                    b.txtStatus.text = "En attente données capteurs..."
                    return@collectLatest
                }
                b.txtCh4.text  = "CH₄ : %.2f %%".format(snap.ch4)
                b.txtCo.text   = "CO  : %d ppm".format(snap.co)
                b.txtO2.text   = "O₂  : %.1f %%".format(snap.o2)
                b.txtTemp.text = "Temp: %.1f °C".format(snap.temp)
                b.txtBat.text  = "Bat : %d %%".format(snap.battery)
                b.txtStatus.text = "Maj : ${snap.ts}"

                // Bandeau alerte
                if (snap.isAlert) {
                    b.alertBar.visibility = android.view.View.VISIBLE
                    b.alertBar.setBackgroundColor(Color.RED)
                    b.alertBar.text = "⚠ ALERTE — Quittez la zone"
                } else {
                    b.alertBar.visibility = android.view.View.GONE
                }
            }
        }
    }
}
