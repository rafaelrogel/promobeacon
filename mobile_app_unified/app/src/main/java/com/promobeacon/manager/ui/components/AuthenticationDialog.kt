package com.promobeacon.manager.ui.components

import android.app.Dialog
import android.content.Context
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.Window
import android.widget.Toast
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.platform.ComposeView
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.fragment.app.DialogFragment
import androidx.lifecycle.lifecycleScope
import com.google.android.material.dialog.MaterialAlertDialogBuilder
import com.promobeacon.manager.R
import com.promobeacon.manager.data.ble.AuthenticationState
import com.promobeacon.manager.databinding.DialogAuthenticationBinding
import com.promobeacon.manager.ui.theme.PromoBeaconManagerTheme
import kotlinx.coroutines.launch

/**
 * Authentication dialog for device authentication
 */
class AuthenticationDialog(
    private val authenticationState: kotlinx.coroutines.flow.Flow<AuthenticationState>,
    private val deviceName: String,
    private val onAuthenticate: (String) -> Unit,
    private val onCancelled: () -> Unit
) : DialogFragment() {

    private var _binding: DialogAuthenticationBinding? = null
    private val binding get() = _binding!!

    override fun onCreateDialog(savedInstanceState: Bundle?): Dialog {
        _binding = DialogAuthenticationBinding.inflate(LayoutInflater.from(context))

        binding.titleText.setText(getString(R.string.authentication_required))
        binding.subtitleText.setText(getString(R.string.enter_auth_token_for, deviceName))
        binding.hintText.setText(getString(R.string.token_hint_format))

        binding.cancelButton.setOnClickListener {
            dismiss()
            onCancelled()
        }

        binding.authenticateButton.setOnClickListener {
            authenticate()
        }

        // Observe authentication state
        lifecycleScope.launch {
            authenticationState.collect { state ->
                updateUI(state)
            }
        }

        val dialog = MaterialAlertDialogBuilder(requireContext())
            .setView(binding.root)
            .setCancelable(false)
            .create()

        dialog.window?.requestFeature(Window.FEATURE_NO_TITLE)
        return dialog
    }

    override fun onStart() {
        super.onStart()
        dialog?.show()
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }

    private fun updateUI(state: AuthenticationState) {
        when (state) {
            AuthenticationState.NOT_AUTHENTICATED -> {
                binding.progressIndicator.setVisibility(View.GONE)
                binding.authenticateButton.setEnabled(true)
                binding.tokenInput.setEnabled(true)
            }
            AuthenticationState.REQUIRED -> {
                binding.progressIndicator.setVisibility(View.GONE)
                binding.authenticateButton.setEnabled(true)
                binding.tokenInput.setEnabled(true)
                binding.errorText.setVisibility(View.GONE)
            }
            AuthenticationState.AUTHENTICATING -> {
                binding.progressIndicator.setVisibility(View.VISIBLE)
                binding.authenticateButton.setEnabled(false)
                binding.tokenInput.setEnabled(false)
                binding.errorText.setVisibility(View.GONE)
            }
            AuthenticationState.AUTHENTICATED -> {
                binding.progressIndicator.setVisibility(View.GONE)
                Toast.makeText(context, R.string.authentication_successful, Toast.LENGTH_SHORT).show()
                dismiss()
            }
            AuthenticationState.FAILED -> {
                binding.progressIndicator.setVisibility(View.GONE)
                binding.authenticateButton.setEnabled(true)
                binding.tokenInput.setEnabled(true)
                binding.errorText.setText(getString(R.string.authentication_failed))
                binding.errorText.setVisibility(View.VISIBLE)
                binding.tokenInput.text?.clear()
            }
            AuthenticationState.LOCKED -> {
                binding.progressIndicator.setVisibility(View.GONE)
                binding.authenticateButton.setEnabled(false)
                binding.tokenInput.setEnabled(false)
                binding.errorText.setText(getString(R.string.device_locked))
                binding.errorText.setVisibility(View.VISIBLE)
            }
        }
    }

    private fun authenticate() {
        val token = binding.tokenInput.text?.toString() ?: ""

        if (token.length != 32) {
            binding.errorText.setText(getString(R.string.invalid_token_length))
            binding.errorText.setVisibility(View.VISIBLE)
            return
        }

        binding.errorText.setVisibility(View.GONE)
        onAuthenticate(token)
    }

    fun dismissDialog() {
        dialog?.dismiss()
    }

    fun isShowing(): Boolean = dialog?.isShowing == true
}
