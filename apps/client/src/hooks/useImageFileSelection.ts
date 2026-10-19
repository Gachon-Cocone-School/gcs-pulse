'use client';

import { useCallback, useEffect, useState } from 'react';

interface ImageFileSelection {
  file: File | null;
  previewUrl: string | null;
}

export function useImageFileSelection() {
  const [selection, setSelection] = useState<ImageFileSelection>({ file: null, previewUrl: null });

  const selectFile = useCallback((file: File | null) => {
    setSelection({
      file,
      previewUrl: file ? URL.createObjectURL(file) : null,
    });
  }, []);

  useEffect(() => {
    const previewUrl = selection.previewUrl;
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [selection.previewUrl]);

  return { ...selection, selectFile };
}
