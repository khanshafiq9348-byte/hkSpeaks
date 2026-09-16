"use client";

import React from "react";
import UploadedVoiceModal, { UploadedVoiceModalProps } from "./UploadedVoiceModal";
import { Voice } from "./VoiceSelectorModal";

interface VoiceCloneModalProps {
  isOpen: boolean;
  onClose: () => void;
  selectedVoiceId?: string;
  onSuccess?: (voice?: Voice) => void;
  onSelectVoice?: (voice: Voice) => void;
}

/**
 * Unified VoiceCloneModal:
 * Consolidates all clone modals onto the clean white "Select uploaded voice" reference design.
 * Eliminates duplicate/separate upload implementations.
 */
export default function VoiceCloneModal({
  isOpen,
  onClose,
  selectedVoiceId,
  onSuccess,
  onSelectVoice,
}: VoiceCloneModalProps) {
  return (
    <UploadedVoiceModal
      isOpen={isOpen}
      onClose={onClose}
      selectedVoiceId={selectedVoiceId}
      onSelectVoice={(voice) => {
        if (onSelectVoice) onSelectVoice(voice);
        if (onSuccess) onSuccess(voice);
      }}
      onSuccess={onSuccess}
    />
  );
}
