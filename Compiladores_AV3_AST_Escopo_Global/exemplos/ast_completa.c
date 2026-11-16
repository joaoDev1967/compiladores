#include <stdio.h>

int soma(int, int);

int soma(int a, int b) {
    return a + b;
}

int main(void) {
    int total = 0;
    for (int i = 0; i < 3; i++) {
        if (i % 2 == 0) {
            total = total + i;
        } else {
            total += 1;
        }
    }
    while (total < 5) {
        total++;
    }
    do {
        total--;
    } while (total > 3);
    switch (total) {
        case 3:
            printf("total = %d\n", total);
            break;
        default:
            total = 0;
            break;
    }
    printf("soma = %d\n", soma(total, 1));
    return 0;
}
