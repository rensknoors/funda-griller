import { Dialog } from "@base-ui/react/dialog";
import { ChevronLeft, ChevronRight } from "lucide-react";

import type { CasePhoto } from "./api";

/** One Listing photo at full size, stepping through the others with the arrows or arrow keys. */
export function PhotoViewer(props: {
  photos: CasePhoto[];
  viewing: CasePhoto | null;
  onView: (photo: CasePhoto | null) => void;
}) {
  const { photos, viewing } = props;
  const index = viewing ? photos.findIndex((p) => p.number === viewing.number) : -1;
  const step = (by: number) => {
    if (index < 0 || photos.length === 0) return;
    props.onView(photos[(index + by + photos.length) % photos.length]);
  };

  return (
    <Dialog.Root open={viewing !== null} onOpenChange={(open) => !open && props.onView(null)}>
      <Dialog.Portal>
        <Dialog.Backdrop className="dialog-backdrop" />
        <Dialog.Popup
          className="dialog photo-dialog"
          onKeyDown={(event) => {
            if (event.key === "ArrowRight") step(1);
            if (event.key === "ArrowLeft") step(-1);
          }}
        >
          <Dialog.Title>{viewing && `Foto ${viewing.number}`}</Dialog.Title>
          {viewing && (
            <div className="photo-stage">
              <img src={viewing.url} alt={`Foto ${viewing.number}`} />
              {photos.length > 1 && (
                <>
                  <button type="button" className="photo-step previous" aria-label="Vorige foto" onClick={() => step(-1)}>
                    <ChevronLeft size={22} aria-hidden="true" />
                  </button>
                  <button type="button" className="photo-step next" aria-label="Volgende foto" onClick={() => step(1)}>
                    <ChevronRight size={22} aria-hidden="true" />
                  </button>
                </>
              )}
            </div>
          )}
          <div className="row">
            {index >= 0 && photos.length > 1 && (
              <span className="muted photo-position">
                {index + 1} van {photos.length}
              </span>
            )}
            <Dialog.Close>Sluiten</Dialog.Close>
          </div>
        </Dialog.Popup>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
