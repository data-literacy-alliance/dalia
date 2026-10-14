import { ItemObject } from '@/lib/types/ItemTypes';
import { BASE_PATH } from '@/lib/settings.mjs';

function mapStringToNumber(str: string) {
  // Convert the string to a number by summing up ASCII values of its characters
  let total = 0;
  for (let i = 0; i < str.length; i++) {
    total += str.charCodeAt(i);
  }

  // Map the total to a number between 1 and 4
  return (total % 4) + 1;
}

export default function getImage({ id }: ItemObject) {
  return `${BASE_PATH}/images/t0${mapStringToNumber(id)}.png`;
}
